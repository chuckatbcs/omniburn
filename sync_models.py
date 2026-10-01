#!/usr/bin/env python3
"""
Dynamic AI model and pricing synchronization engine.
Pulls live model registry directly from OpenRouter API and LiteLLM feeds.
Detects current frontier models (GPT-6, Grok 4.7, Claude Opus 5.5, Gemini 3.8, Nemotron 3.5, Hermes 4).
"""

import datetime
import json
import os
import sys
import urllib.request

OPENROUTER_URL = "https://openrouter.ai/api/v1/models"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "models_catalog.json")

def fetch_json(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "AIBurnRateTracker/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def sync():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    print(f"[{now_utc.isoformat()}] Fetching live models and current pricing from OpenRouter API...")
    
    data = fetch_json(OPENROUTER_URL)
    raw_models = data.get("data", [])
    print(f"✓ Retrieved {len(raw_models)} models from live feed.")

    # Target providers and their harness mappings
    # Provider prefix -> (Harness Name, Sub ID, Harness Type, Burn Rate Quota Metric)
    harness_map = {
        "openai": {
            "harness": "ChatGPT Plus / Codex",
            "sub_id": "chatgpt-plus",
            "type": "Web, Canvas & Voice / Codex",
            "burn_quota": "Time-window rolling cap (40-80 msgs/3h) + weekly tier cap on Astra/Pro"
        },
        "anthropic": {
            "harness": "Cursor Pro",
            "sub_id": "cursor-pro",
            "type": "Cursor IDE Composer & Agent",
            "burn_quota": "Burns 1 fast credit from 500 fast requests/mo pool, then unlimited slow"
        },
        "x-ai": {
            "harness": "Cursor Pro (Bundled)",
            "sub_id": "cursor-pro",
            "type": "Cursor Code Editor & Grok Bot",
            "burn_quota": "Bundled in $20 Cursor plan ($0 incremental charge; shares fast pool)"
        },
        "google": {
            "harness": "Gemini Pro / Antigravity",
            "sub_id": "gemini-pro-antigravity",
            "type": "Antigravity Agentic IDE & Studio",
            "burn_quota": "Generous high-capacity agent loops + 1M-2M context per prompt"
        },
        "nvidia": {
            "harness": "NVIDIA NIM (Free Tier)",
            "sub_id": "nvidia-nim",
            "type": "build.nvidia.com Cloud NIM",
            "burn_quota": "1,000 free API credits / rate-limited developer endpoints ($0/mo)"
        },
        "nousresearch": {
            "harness": "NousResearch (Free Account)",
            "sub_id": "nous-research",
            "type": "Nous Portal & Community Discord",
            "burn_quota": "Free community queue / open weights inference ($0/mo)"
        }
    }

    # Curate frontier flagship models from live catalog
    frontier_models = []
    
    # Track the best frontier models per provider
    seen_prefixes = set()

    # Prioritize newest models sorted by created timestamp descending
    sorted_raw = sorted(raw_models, key=lambda x: x.get("created", 0), reverse=True)

    for m in sorted_raw:
        mid = m.get("id", "")
        if ":" in mid and not mid.endswith(":free"):
            continue # Skip batch/special variants unless free tier
            
        provider_key = mid.split("/")[0] if "/" in mid else ""
        if provider_key not in harness_map:
            continue

        h_info = harness_map[provider_key]
        created_ts = m.get("created", 0)
        dt_str = datetime.datetime.fromtimestamp(created_ts, datetime.timezone.utc).strftime("%Y-%m-%d") if created_ts else "2026"
        
        pricing = m.get("pricing", {})
        p_in = round(float(pricing.get("prompt", 0) or 0) * 1_000_000, 2)
        p_out = round(float(pricing.get("completion", 0) or 0) * 1_000_000, 2)
        ctx = m.get("context_length", 0)

        # Comparative advantage logic based on model family
        edge = ""
        name = m.get("name", mid)
        
        if "gpt-6-astra" in mid:
            edge = "Flagship multi-step reasoning model; highest STEM & PhD-level benchmark scores."
        elif "gpt-6-sol" in mid:
            edge = "High-speed reasoning workhorse with 1.05M context; ideal for fast logic iteration."
        elif "gpt-6-luna" in mid:
            edge = "Ultra-efficient omni-modal model with 1.05M working memory; lowest token cost."
        elif "claude-opus-5.5" in mid:
            edge = "State-of-the-art coding and agentic file diffs inside Cursor; 1M context."
        elif "claude-fable" in mid:
            edge = "Advanced narrative synthesis and multi-system architectural design."
        elif "grok-4.7" in mid:
            edge = "Frontier real-time web grounding and Grok bot assistance bundled in Cursor at $0 extra."
        elif "grok-4.20" in mid:
            edge = "Massive 2M context multi-agent reasoning with native tool grounding."
        elif "gemini-3.8-flash" in mid:
            edge = "Sub-100ms first-token latency with 1.05M context; native Antigravity agent execution."
        elif "gemini-3.7-flash" in mid:
            edge = "High-throughput multimodal agent loop workhorse; 1M context."
        elif "gemini-3.1-pro" in mid or "gemini-3-pro" in mid:
            edge = "Deep code synthesis, full-repository comprehension, and multimodal analysis."
        elif "nemotron-3.5-lightning" in mid:
            edge = "Hardware-optimized low-latency inference on TensorRT-LLM with free developer tier."
        elif "nemotron-3-ultra" in mid:
            edge = "550B dense reasoning model available in free developer tier with 1M context."
        elif "hermes-4" in mid:
            edge = "405B flagship open-weights reasoning model with uncensored instruction following."
        else:
            edge = f"Frontier {provider_key.upper()} capability with {ctx:,} token working memory."

        frontier_models.append({
            "id": mid,
            "name": name,
            "vendor": provider_key.capitalize() if provider_key != "x-ai" else "xAI",
            "release_date": dt_str,
            "created_ts": created_ts,
            "harness": h_info["harness"],
            "sub_id": h_info["sub_id"],
            "harness_type": h_info["type"],
            "burn_rate_metric": h_info["burn_quota"],
            "input_per_million": p_in,
            "output_per_million": p_out,
            "context_window": ctx,
            "comparative_advantage": edge
        })

    # Pick top representative frontier models (top 12-15 newest distinct models across user's subscriptions)
    curated = []
    seen_ids = set()
    
    # Specific prioritized lineup from late 2026 feeds:
    prioritized_keys = [
        "openai/gpt-6-luna-pro",
        "openai/gpt-6-sol-pro",
        "anthropic/claude-opus-5.5",
        "x-ai/grok-4.7",
        "openai/gpt-6-astra-pro",
        "google/gemini-3.8-flash",
        "google/gemini-3.7-flash",
        "x-ai/grok-4.6",
        "nvidia/nemotron-3.5-lightning:free",
        "anthropic/claude-opus-5",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "google/gemini-3.1-pro-preview",
        "x-ai/grok-4.20-multi-agent",
        "nousresearch/hermes-4-405b"
    ]

    model_lookup = {m["id"]: m for m in frontier_models}
    for pk in prioritized_keys:
        if pk in model_lookup and pk not in seen_ids:
            curated.append(model_lookup[pk])
            seen_ids.add(pk)

    # Add any other top recent ones
    for m in frontier_models:
        if m["id"] not in seen_ids and len(curated) < 18:
            curated.append(m)
            seen_ids.add(m["id"])

    # Ensure sorted by release date / created_ts descending
    curated = sorted(curated, key=lambda x: x["created_ts"], reverse=True)

    payload = {
        "last_updated": now_utc.isoformat(),
        "total_models_tracked": len(raw_models),
        "frontier_models": curated
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"✓ Saved {len(curated)} newest 2026 frontier models to {OUTPUT_FILE}.")

if __name__ == "__main__":
    sync()
