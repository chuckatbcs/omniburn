#!/usr/bin/env python3
"""
Database persistence module for OmniBurn.
Provides SQLite connection management, schema initialization, and seed data.
"""

import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "burn_tracker.db")

def get_connection(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Subscriptions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        provider TEXT NOT NULL,
        monthly_cost REAL NOT NULL,
        billing_cycle TEXT NOT NULL DEFAULT 'monthly',
        status TEXT NOT NULL DEFAULT 'active',
        description TEXT
    );
    """)

    # 2. Quota Pools Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quota_pools (
        id TEXT PRIMARY KEY,
        sub_id TEXT NOT NULL,
        pool_name TEXT NOT NULL,
        reset_window_hours REAL NOT NULL,
        window_type TEXT NOT NULL,
        ui_granularity_pct INTEGER NOT NULL DEFAULT 1,
        current_pct_remaining INTEGER NOT NULL DEFAULT 100,
        weekly_pct_remaining INTEGER NOT NULL DEFAULT 100,
        last_reset TEXT,
        FOREIGN KEY (sub_id) REFERENCES subscriptions(id)
    );
    """)

    # 3. Models Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        model_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        provider TEXT NOT NULL,
        harness TEXT NOT NULL,
        pool_id TEXT,
        context_window INTEGER,
        input_cost_per_m REAL DEFAULT 0.0,
        output_cost_per_m REAL DEFAULT 0.0,
        reasoning_effort TEXT DEFAULT 'medium',
        speed_mode TEXT DEFAULT 'normal',
        is_frontier INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        first_pass_rate_t2 REAL,
        first_pass_rate_t3 REAL,
        tasks_per_1pct_t2 REAL,
        tasks_per_1pct_t3 REAL,
        last_seen TEXT,
        FOREIGN KEY (pool_id) REFERENCES quota_pools(id)
    );
    """)

    # 4. Task Tiers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_tiers (
        tier_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        typical_tokens_in INTEGER NOT NULL,
        typical_tokens_out INTEGER NOT NULL,
        typical_steps INTEGER NOT NULL,
        description TEXT
    );
    """)

    # 5. Model Task Yields Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_task_yields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id TEXT NOT NULL,
        tier_id INTEGER NOT NULL,
        tasks_per_pool_cycle REAL NOT NULL,
        tasks_per_month REAL NOT NULL,
        cost_per_completed_task REAL NOT NULL,
        api_cost_per_task REAL,
        success_adjusted_tokens INTEGER,
        success_adjusted_seconds REAL,
        quota_first_score REAL,
        time_reliability_score REAL,
        recommendation_notes TEXT,
        FOREIGN KEY (model_id) REFERENCES models(model_id),
        FOREIGN KEY (tier_id) REFERENCES task_tiers(tier_id),
        UNIQUE(model_id, tier_id)
    );
    """)

    # 6. Model Changelog Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_changelog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        model_id TEXT NOT NULL,
        details TEXT NOT NULL
    );
    """)

    # 7. Telemetry Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_runs (
        task_id TEXT PRIMARY KEY,
        matched_pair_id TEXT,
        task_class TEXT NOT NULL,
        model_id TEXT NOT NULL,
        reasoning TEXT,
        timestamp TEXT NOT NULL,
        five_hour_before_pct INTEGER,
        five_hour_after_pct INTEGER,
        weekly_before_pct INTEGER,
        weekly_after_pct INTEGER,
        completed INTEGER NOT NULL,
        first_pass_success INTEGER NOT NULL,
        attempt_number INTEGER NOT NULL,
        tool_calls INTEGER DEFAULT 0,
        agent_steps INTEGER DEFAULT 0,
        input_tokens INTEGER DEFAULT 0,
        cache_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        wall_clock_seconds REAL DEFAULT 0.0,
        sanitized_description TEXT,
        run_type TEXT DEFAULT 'production'
    );
    """)

    # Dynamic migrations for existing databases
    cursor.execute("PRAGMA table_info(model_task_yields);")
    mty_cols = [c[1] for c in cursor.fetchall()]
    if "api_cost_per_task" not in mty_cols:
        cursor.execute("ALTER TABLE model_task_yields ADD COLUMN api_cost_per_task REAL;")

    cursor.execute("PRAGMA table_info(telemetry_runs);")
    tr_cols = [c[1] for c in cursor.fetchall()]
    if "run_type" not in tr_cols:
        cursor.execute("ALTER TABLE telemetry_runs ADD COLUMN run_type TEXT DEFAULT 'production';")
        # Classify existing golden benchmark runs
        cursor.execute("""
            UPDATE telemetry_runs
            SET run_type = 'golden_benchmark'
            WHERE task_class LIKE '%T1:%' OR task_class LIKE '%T2:%' OR task_class LIKE '%T3:%' OR task_class LIKE '%T4:%';
        """)

    # Harmonize canonical task classes
    cursor.execute("UPDATE telemetry_runs SET task_class = 'Tier 2: Standard Engineering' WHERE task_class = 'Tier 2';")

    conn.commit()
    seed_defaults(conn)
    conn.close()
    print(f"Database initialized successfully at: {db_path or DB_PATH}")

def seed_defaults(conn):
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Seed Subscriptions
    subs = [
        ("gemini-pro-antigravity", "Google AI Pro (Antigravity)", "Google", 19.99, "monthly", "active", "Includes Antigravity IDE, 2 independent 5h rolling pools (Gemini & Claude/GPT), 1M-2M context"),
        ("cursor-pro", "Cursor Pro", "Cursor", 20.00, "monthly", "active", "Includes Cursor Models pool (Composer 2.5, Grok 4.7) and Other Models pool (Claude Sonnet/Opus, GPT-5.6)"),
        ("chatgpt-plus", "ChatGPT Plus Work / Codex", "OpenAI", 20.00, "monthly", "active", "Web, Canvas, Voice, Codex with local 5h capacity ranges (Astra, Sol, Terra, Luna)"),
        ("nvidia-nim", "NVIDIA NIM Free Tier", "NVIDIA", 0.00, "monthly", "active", "1,000 monthly inference credits on build.nvidia.com (Llama 3.3, Nemotron 3.5)"),
        ("nousresearch", "NousResearch Portal", "NousResearch", 0.00, "monthly", "active", "Community access to frontier open reasoning models (Hermes 3/4)")
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO subscriptions (id, name, provider, monthly_cost, billing_cycle, status, description)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, subs)

    # 2. Seed Quota Pools
    pools = [
        ("gemini_models", "gemini-pro-antigravity", "Pool A: Gemini Models", 5.0, "rolling_5h", 1, 100, 100, now_iso),
        ("claude_gpt_models", "gemini-pro-antigravity", "Pool B: Claude & GPT Models", 5.0, "rolling_5h", 1, 100, 100, now_iso),
        ("cursor_models", "cursor-pro", "Cursor Models Pool", 720.0, "monthly_billing", 1, 100, 100, now_iso),
        ("other_models", "cursor-pro", "Other Models Pool", 720.0, "monthly_billing", 1, 100, 100, now_iso),
        ("chatgpt_local", "chatgpt-plus", "ChatGPT Local 5h Capacity", 5.0, "rolling_5h", 5, 100, 100, now_iso),
        ("nvidia_free", "nvidia-nim", "NVIDIA NIM Monthly Credits", 720.0, "monthly_billing", 1, 100, 100, now_iso),
        ("nous_free", "nousresearch", "Nous Open Endpoints", 24.0, "daily_burstable", 1, 100, 100, now_iso)
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO quota_pools (id, sub_id, pool_name, reset_window_hours, window_type, ui_granularity_pct, current_pct_remaining, weekly_pct_remaining, last_reset)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, pools)

    # 3. Seed Task Tiers
    tiers = [
        (1, "Tier 1: Micro-Task", 1000, 500, 2, "Formatting, docstrings, syntax fixes, regex, unit test stubs"),
        (2, "Tier 2: Standard Engineering", 6500, 1500, 8, "Refactoring modules, writing API routes, multi-file unit tests, bug fixing"),
        (3, "Tier 3: Long-Horizon Agent Coding", 30000, 4500, 18, "Greenfield feature architecture, migrations, autonomous multi-turn debugging"),
        (4, "Tier 4: Massive Context & Synthesis", 150000, 10000, 40, "Repo-wide audits, large codebase refactoring, multi-million token ingestion")
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO task_tiers (tier_id, name, typical_tokens_in, typical_tokens_out, typical_steps, description)
    VALUES (?, ?, ?, ?, ?, ?);
    """, tiers)

    # 4. Seed Frontier & Key Harness Models
    key_models = [
        # Antigravity Pool A
        ("gemini-3.8-flash-medium", "Gemini 3.8 Flash (Medium)", "Google", "Antigravity", "gemini_models", 1000000, 0.10, 0.40, "medium", "normal", 1, 1, 0.90, 0.60, 20.0, 5.0, now_iso),
        ("gemini-3.8-flash-low", "Gemini 3.8 Flash (Low)", "Google", "Antigravity", "gemini_models", 1000000, 0.08, 0.30, "low", "normal", 1, 1, 0.85, 0.50, 25.0, 6.0, now_iso),
        ("gemini-3.1-pro-high", "Gemini 3.1 Pro (High)", "Google", "Antigravity", "gemini_models", 2000000, 1.25, 5.00, "high", "normal", 1, 1, 0.95, 0.75, 4.0, 2.0, now_iso),
        # Antigravity Pool B
        ("claude-sonnet-4-6", "Claude Sonnet 4.6", "Anthropic", "Antigravity", "claude_gpt_models", 200000, 3.00, 15.00, "medium", "normal", 1, 1, 0.90, 0.55, 3.33, 2.0, now_iso),
        ("claude-opus-4-6-thinking", "Claude Opus 4.6 (Thinking)", "Anthropic", "Antigravity", "claude_gpt_models", 200000, 5.00, 25.00, "high", "normal", 1, 1, 0.95, 0.75, 1.54, 1.0, now_iso),
        ("gpt-oss-120b-medium", "GPT-OSS 120B (Medium)", "Open Source", "Antigravity", "claude_gpt_models", 128000, 0.50, 2.00, "medium", "normal", 0, 1, 0.80, 0.45, 5.0, 2.5, now_iso),
        # Cursor Models
        ("composer-2.5-normal", "Composer 2.5 (Normal)", "Cursor", "Cursor IDE", "cursor_models", 128000, 1.50, 6.00, "medium", "normal", 1, 1, 0.88, 0.65, 0.0, 0.0, now_iso),
        ("composer-2.5-fast", "Composer 2.5 (Fast)", "Cursor", "Cursor IDE", "cursor_models", 128000, 1.50, 6.00, "medium", "fast", 1, 1, 0.88, 0.65, 0.0, 0.0, now_iso),
        ("grok-4.7", "Grok 4.7 (Cursor Bundled)", "xAI", "Cursor IDE", "cursor_models", 256000, 2.00, 10.00, "high", "normal", 1, 1, 0.89, 0.70, 0.0, 0.0, now_iso),
        # Cursor Other Models
        ("claude-sonnet-5", "Claude Sonnet 5", "Anthropic", "Cursor IDE", "other_models", 200000, 3.00, 15.00, "medium", "normal", 1, 1, 0.92, 0.70, 0.0, 0.0, now_iso),
        ("claude-opus-5-5", "Claude Opus 5.5", "Anthropic", "Cursor IDE", "other_models", 200000, 5.00, 25.00, "high", "normal", 1, 1, 0.96, 0.82, 0.0, 0.0, now_iso),
        # ChatGPT Plus
        ("gpt-6-astra", "GPT-6 Astra Pro", "OpenAI", "ChatGPT Plus / Codex", "chatgpt_local", 256000, 5.00, 25.00, "high", "normal", 1, 1, 0.95, 0.80, 0.0, 0.0, now_iso),
        ("gpt-5.6-sol", "GPT-5.6 Sol Pro", "OpenAI", "ChatGPT Plus / Codex", "chatgpt_local", 128000, 2.50, 10.00, "medium", "normal", 1, 1, 0.91, 0.68, 0.0, 0.0, now_iso),
        ("gpt-5.6-terra", "GPT-5.6 Terra", "OpenAI", "ChatGPT Plus / Codex", "chatgpt_local", 128000, 1.00, 4.00, "low", "normal", 1, 1, 0.86, 0.55, 0.0, 0.0, now_iso),
        ("gpt-5.6-luna", "GPT-5.6 Luna", "OpenAI", "ChatGPT Plus / Codex", "chatgpt_local", 128000, 0.25, 1.00, "low", "fast", 0, 1, 0.80, 0.40, 0.0, 0.0, now_iso),
        # Free Tiers
        ("nemotron-3.5-lightning", "Nemotron 3.5 Lightning", "NVIDIA", "NVIDIA NIM", "nvidia_free", 128000, 0.00, 0.00, "medium", "fast", 1, 1, 0.85, 0.52, 0.0, 0.0, now_iso),
        ("hermes-4-70b", "Hermes 4 70B", "NousResearch", "Nous Portal", "nous_free", 128000, 0.00, 0.00, "medium", "normal", 1, 1, 0.84, 0.50, 0.0, 0.0, now_iso)
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO models (
        model_id, display_name, provider, harness, pool_id, context_window,
        input_cost_per_m, output_cost_per_m, reasoning_effort, speed_mode,
        is_frontier, is_active, first_pass_rate_t2, first_pass_rate_t3,
        tasks_per_1pct_t2, tasks_per_1pct_t3, last_seen
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, key_models)

    # Telemetry is intentionally not bundled with the application. Import local
    # observations through the runtime logger instead of committing user history.

    conn.commit()

if __name__ == "__main__":
    init_db()
