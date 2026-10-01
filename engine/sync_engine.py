#!/usr/bin/env python3
"""
Automated synchronization engine for OmniBurn.
Discovers local Antigravity models via `agy models`, ingests live provider registries
from OpenRouter API, detects pricing/quota changes, logs diffs to `model_changelog`,
and triggers automatic yield recalculation.
"""

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from engine.db import get_connection
from engine.calculator import recalculate_all_yields

OPENROUTER_URL = "https://openrouter.ai/api/v1/models"

def fetch_openrouter_models(timeout=8):
    try:
        req = urllib.request.Request(OPENROUTER_URL, headers={"User-Agent": "OmniBurn/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("data", [])
    except Exception as e:
        print(f"Notice: OpenRouter API live fetch skipped or offline ({e}). Using local/cached catalog.")
        return []

def fetch_local_agy_models():
    """Runs `agy models` CLI to detect current selectable models in Antigravity."""
    models = []
    error = None
    try:
        import re
        out = subprocess.check_output(["agy", "models"], stderr=subprocess.PIPE, timeout=5).decode("utf-8")
        for raw_line in out.strip().splitlines():
            line = re.sub(r'^[⠋⠙⠹⠸⠼⠴⠦⠧⠇\s]*Fetching available models\.\.\.', '', raw_line).strip()
            if not line:
                continue
            parts = re.split(r'\t+|\s{2,}', line)
            if len(parts) >= 2:
                model_id = parts[0].strip()
                name = parts[1].strip()
                
                # Determine pool and reasoning
                if "gemini" in model_id:
                    pool = "gemini_models"
                    provider = "Google"
                elif "claude" in model_id:
                    pool = "claude_gpt_models"
                    provider = "Anthropic"
                else:
                    pool = "claude_gpt_models"
                    provider = "Open Source"
                
                if "high" in model_id or "thinking" in model_id:
                    reasoning = "high"
                elif "low" in model_id:
                    reasoning = "low"
                else:
                    reasoning = "medium"
                
                context = 2000000 if "pro" in model_id else (1000000 if "gemini" in model_id else 200000)
                
                models.append({
                    "model_id": model_id,
                    "display_name": name,
                    "provider": provider,
                    "harness": "Antigravity",
                    "pool_id": pool,
                    "context_window": context,
                    "reasoning_effort": reasoning,
                    "speed_mode": "normal",
                    "is_frontier": 1 if ("3.8" in model_id or "3.1" in model_id or "claude" in model_id) else 0
                })
    except Exception as e:
        error = str(e)
        print(f"Notice: agy CLI check skipped or failed ({e}).")
    return models, error

def fetch_local_ollama_models():
    """Detects locally installed models in Ollama via HTTP endpoint or CLI."""
    models = []
    error = None
    # 1. Try local Ollama HTTP API (fastest, structured)
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"User-Agent": "OmniBurn/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode("utf-8"))
            for m in data.get("models", []):
                name = m.get("name", "")
                if not name:
                    continue
                details = m.get("details", {})
                param_size = details.get("parameter_size", "")
                ctx = details.get("context_length", 131072) or 131072
                caps = m.get("capabilities", [])
                reasoning = "high" if "thinking" in caps else ("low" if "embedding" in caps else "medium")
                display_name = f"{name} (Local {param_size})" if param_size else f"{name} (Local)"
                models.append({
                    "model_id": f"ollama/{name}",
                    "display_name": display_name,
                    "provider": "Ollama / Local",
                    "harness": "Ollama (Local)",
                    "pool_id": "local_ollama",
                    "context_window": ctx,
                    "input_cost_per_m": 0.0,
                    "output_cost_per_m": 0.0,
                    "reasoning_effort": reasoning,
                    "speed_mode": "fast",
                    "is_frontier": 0,
                    "first_pass_rate_t2": 0.85,
                    "first_pass_rate_t3": 0.50,
                    "tasks_per_1pct_t2": 100.0,
                    "tasks_per_1pct_t3": 50.0,
                })
            if models:
                return models, None
    except Exception as e:
        error = str(e)

    # 2. Fallback to CLI `ollama list`
    try:
        out = subprocess.check_output(["ollama", "list"], stderr=subprocess.PIPE, timeout=2).decode("utf-8")
        lines = out.strip().splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    name = parts[0].strip()
                    models.append({
                        "model_id": f"ollama/{name}",
                        "display_name": f"{name} (Local)",
                        "provider": "Ollama / Local",
                        "harness": "Ollama (Local)",
                        "pool_id": "local_ollama",
                        "context_window": 131072,
                        "input_cost_per_m": 0.0,
                        "output_cost_per_m": 0.0,
                        "reasoning_effort": "medium",
                        "speed_mode": "fast",
                        "is_frontier": 0,
                        "first_pass_rate_t2": 0.85,
                        "first_pass_rate_t3": 0.50,
                        "tasks_per_1pct_t2": 100.0,
                        "tasks_per_1pct_t3": 50.0,
                    })
            if models:
                return models, None
    except Exception as e:
        error = str(e)

    return models, error

def sync_models(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    changes_logged = []

    # 1. Fetch current models in DB
    cursor.execute("SELECT model_id, input_cost_per_m, output_cost_per_m, is_active, harness FROM models")
    existing_models = {row["model_id"]: dict(row) for row in cursor.fetchall()}

    # 2. Ingest local Antigravity models
    agy_models, agy_err = fetch_local_agy_models()
    if agy_err:
        changes_logged.append({"event": "SYNC_WARNING", "source": "agy_cli", "details": agy_err})

    # Prune models no longer active in Antigravity
    if agy_models:
        active_agy_ids = {m["model_id"] for m in agy_models}
        for mid, old in existing_models.items():
            if old.get("harness") == "Antigravity" and mid not in active_agy_ids and old.get("is_active") == 1:
                cursor.execute("UPDATE models SET is_active = 0 WHERE model_id = ?", (mid,))
                cursor.execute("""
                    INSERT INTO model_changelog (timestamp, event_type, model_id, details)
                    VALUES (?, 'MODEL_DEPRECATED', ?, ?);
                """, (now_iso, mid, "Antigravity model no longer reported by agy models CLI"))
                changes_logged.append({"event": "MODEL_DEPRECATED", "model_id": mid})

    for m in agy_models:
        mid = m["model_id"]
        if mid not in existing_models:
            cursor.execute("""
                INSERT INTO models (
                    model_id, display_name, provider, harness, pool_id,
                    context_window, reasoning_effort, speed_mode, is_frontier,
                    is_active, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
            """, (
                mid, m["display_name"], m["provider"], m["harness"], m["pool_id"],
                m["context_window"], m["reasoning_effort"], m["speed_mode"],
                m["is_frontier"], now_iso
            ))
            cursor.execute("""
                INSERT INTO model_changelog (timestamp, event_type, model_id, details)
                VALUES (?, 'NEW_MODEL', ?, ?);
            """, (now_iso, mid, f"Discovered new Antigravity local model: {m['display_name']} ({m['pool_id']})"))
            changes_logged.append({"event": "NEW_MODEL", "model_id": mid, "name": m["display_name"]})
        else:
            cursor.execute("UPDATE models SET last_seen = ?, is_active = 1 WHERE model_id = ?", (now_iso, mid))

    # 3. Ingest local Ollama models
    ollama_models, ollama_err = fetch_local_ollama_models()
    if ollama_models:
        # Ensure subscription and pool exist
        cursor.execute("""
            INSERT OR IGNORE INTO subscriptions (id, name, provider, monthly_cost, billing_cycle, status, description)
            VALUES ('local-ollama', 'Local Ollama Host', 'Localhost', 0.00, 'monthly', 'active', 'Locally running open weights inference via Ollama');
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO quota_pools (id, sub_id, pool_name, reset_window_hours, window_type, ui_granularity_pct, current_pct_remaining, weekly_pct_remaining, last_reset)
            VALUES ('local_ollama', 'local-ollama', 'Local GPU/CPU Inference', 720.0, 'unmetered', 1, 100, 100, ?);
        """, (now_iso,))
        for om in ollama_models:
            omid = om["model_id"]
            if omid not in existing_models:
                cursor.execute("""
                    INSERT INTO models (
                        model_id, display_name, provider, harness, pool_id,
                        context_window, input_cost_per_m, output_cost_per_m,
                        reasoning_effort, speed_mode, is_frontier,
                        first_pass_rate_t2, first_pass_rate_t3,
                        tasks_per_1pct_t2, tasks_per_1pct_t3,
                        is_active, last_seen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
                """, (
                    omid, om["display_name"], om["provider"], om["harness"], om["pool_id"],
                    om["context_window"], om["input_cost_per_m"], om["output_cost_per_m"],
                    om["reasoning_effort"], om["speed_mode"], om["is_frontier"],
                    om["first_pass_rate_t2"], om["first_pass_rate_t3"],
                    om["tasks_per_1pct_t2"], om["tasks_per_1pct_t3"],
                    now_iso
                ))
                cursor.execute("""
                    INSERT INTO model_changelog (timestamp, event_type, model_id, details)
                    VALUES (?, 'NEW_MODEL', ?, ?);
                """, (now_iso, omid, f"Discovered local Ollama model: {om['display_name']}"))
                changes_logged.append({"event": "NEW_MODEL", "model_id": omid, "name": om["display_name"]})
            else:
                cursor.execute("UPDATE models SET last_seen = ?, is_active = 1 WHERE model_id = ?", (now_iso, omid))

    # 3. Ingest OpenRouter feed for key frontier models
    openrouter_list = fetch_openrouter_models()
    for rm in openrouter_list:
        rm_id = rm.get("id", "")
        pricing = rm.get("pricing", {})
        try:
            in_cost = float(pricing.get("prompt", 0)) * 1000000.0
            out_cost = float(pricing.get("completion", 0)) * 1000000.0
        except (ValueError, TypeError):
            in_cost, out_cost = 0.0, 0.0

        # Check if model is relevant to our tracked stack
        relevant_pool = None
        harness = None
        if "anthropic/claude" in rm_id:
            relevant_pool = "other_models"
            harness = "Cursor (Other Models)"
        elif "x-ai/grok" in rm_id:
            relevant_pool = "cursor_models"
            harness = "Cursor (Cursor Models)"
        elif "openai/gpt" in rm_id:
            relevant_pool = "chatgpt_local"
            harness = "ChatGPT / Codex"

        if relevant_pool and rm_id in existing_models:
            old = existing_models[rm_id]
            # Price change check
            if abs(old["input_cost_per_m"] - in_cost) > 0.05 or abs(old["output_cost_per_m"] - out_cost) > 0.05:
                cursor.execute("""
                    UPDATE models
                    SET input_cost_per_m = ?, output_cost_per_m = ?, last_seen = ?
                    WHERE model_id = ?
                """, (in_cost, out_cost, now_iso, rm_id))
                details = f"Price changed: In ${old['input_cost_per_m']:.2f} -> ${in_cost:.2f}, Out ${old['output_cost_per_m']:.2f} -> ${out_cost:.2f}"
                cursor.execute("""
                    INSERT INTO model_changelog (timestamp, event_type, model_id, details)
                    VALUES (?, 'PRICE_CHANGE', ?, ?);
                """, (now_iso, rm_id, details))
                changes_logged.append({"event": "PRICE_CHANGE", "model_id": rm_id, "details": details})

    conn.commit()

    # 4. Automatically recalculate yields if changes occurred
    recalculate_all_yields(conn)
    conn.close()

    summary = {
        "status": "ok",
        "timestamp": now_iso,
        "local_agy_models_synced": len(agy_models),
        "openrouter_models_scanned": len(openrouter_list),
        "changes_count": len(changes_logged),
        "changes": changes_logged
    }
    print(f"Sync complete: {len(changes_logged)} changes logged. Yields updated.")
    return summary

if __name__ == "__main__":
    res = sync_models()
    print(json.dumps(res, indent=2))
