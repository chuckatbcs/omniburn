#!/usr/bin/env python3
"""
Task yield, burn rate, and success-adjusted resource calculator for OmniBurn.
Implements consensus v7 statistical adjustments across Workload Tiers 1-4.
Calculates both fixed subscription cost-per-task and raw API benchmark cost-per-task.
"""

import math
from engine.db import get_connection

# Baseline Workload Specifications
TIER_SPECS = {
    1: {"name": "Tier 1: Micro-Task", "in": 1000, "out": 500, "steps": 2, "base_sec": 15.0},
    2: {"name": "Tier 2: Standard Engineering", "in": 6500, "out": 1500, "steps": 8, "base_sec": 65.0},
    3: {"name": "Tier 3: Long-Horizon Agent Coding", "in": 30000, "out": 4500, "steps": 18, "base_sec": 220.0},
    4: {"name": "Tier 4: Massive Context & Synthesis", "in": 150000, "out": 10000, "steps": 40, "base_sec": 600.0}
}

# Empirical V7 Ground Truth (Tasks per 1% visible decrement & Success-Adjusted Metrics)
EMPIRICAL_V7 = {
    ("gemini-3.8-flash-medium", 2): {
        "tasks_per_1pct": 20.0,
        "first_pass_rate": 0.90,
        "att_per_done": 1.10,
        "tokens_per_completed": 7683,
        "sec_per_completed": 70.9,
        "steps_per_completed": 7.3
    },
    ("gemini-3.8-flash-medium", 3): {
        "tasks_per_1pct": 5.0,
        "first_pass_rate": 0.60,
        "att_per_done": 1.45,
        "tokens_per_completed": 104206,
        "sec_per_completed": 448.4,
        "steps_per_completed": 44.35
    },
    ("gemini-3.1-pro-high", 2): {
        "tasks_per_1pct": 4.0,
        "first_pass_rate": 0.95,
        "att_per_done": 1.05,
        "tokens_per_completed": 10982,
        "sec_per_completed": 113.2,
        "steps_per_completed": 8.55
    },
    ("gemini-3.1-pro-high", 3): {
        "tasks_per_1pct": 2.0,
        "first_pass_rate": 0.75,
        "att_per_done": 1.25,
        "tokens_per_completed": 44284,
        "sec_per_completed": 285.0,
        "steps_per_completed": 21.05
    },
    ("claude-sonnet-4-6", 2): {
        "tasks_per_1pct": 3.33,
        "first_pass_rate": 0.90,
        "att_per_done": 1.10,
        "tokens_per_completed": 18106,
        "sec_per_completed": 103.5,
        "steps_per_completed": 8.5
    },
    ("claude-sonnet-4-6", 3): {
        "tasks_per_1pct": 2.0,
        "first_pass_rate": 0.55,
        "att_per_done": 1.45,
        "tokens_per_completed": 45593,
        "sec_per_completed": 315.2,
        "steps_per_completed": 20.55
    },
    ("claude-opus-4-6-thinking", 2): {
        "tasks_per_1pct": 1.54,
        "first_pass_rate": 0.95,
        "att_per_done": 1.05,
        "tokens_per_completed": 19269,
        "sec_per_completed": 127.0,
        "steps_per_completed": 8.1
    },
    ("claude-opus-4-6-thinking", 3): {
        "tasks_per_1pct": 1.0,
        "first_pass_rate": 0.75,
        "att_per_done": 1.25,
        "tokens_per_completed": 44113,
        "sec_per_completed": 300.2,
        "steps_per_completed": 19.9
    },
    ("claude-opus-4-6-thinking", 4): {
        "tasks_per_1pct": 0.45,
        "first_pass_rate": 0.88,
        "att_per_done": 1.14,
        "tokens_per_completed": 178000,
        "sec_per_completed": 480.0,
        "steps_per_completed": 36.0
    },
    ("claude-opus-5-5", 4): {
        "tasks_per_1pct": 0.50,
        "first_pass_rate": 0.90,
        "att_per_done": 1.11,
        "tokens_per_completed": 172000,
        "sec_per_completed": 450.0,
        "steps_per_completed": 34.0
    },
    ("gpt-6-astra", 4): {
        "tasks_per_1pct": 0.40,
        "first_pass_rate": 0.92,
        "att_per_done": 1.09,
        "tokens_per_completed": 170000,
        "sec_per_completed": 510.0,
        "steps_per_completed": 35.0
    },
    ("gemini-3.1-pro-high", 4): {
        "tasks_per_1pct": 0.70,
        "first_pass_rate": 0.76,
        "att_per_done": 1.32,
        "tokens_per_completed": 215000,
        "sec_per_completed": 540.0,
        "steps_per_completed": 40.0
    },
    ("gpt-6-1-sol", 4): {
        "tasks_per_1pct": 0.75,
        "first_pass_rate": 0.78,
        "att_per_done": 1.28,
        "tokens_per_completed": 200000,
        "sec_per_completed": 420.0,
        "steps_per_completed": 38.0
    }
}

def get_telemetry_metrics(conn, model_id, tier_id):
    """
    Derive dynamic empirical metrics directly from telemetry_runs.
    Prioritizes uncontaminated empirical lanes (EXP-*) or verified production runs.
    Returns dict if sample size >= 3 completed tasks and quota delta observed, else None.
    """
    if conn is None:
        return None
    cursor = conn.cursor()
    # Check for empirical test dataset first to avoid synthetic benchmark contamination
    cursor.execute("""
        SELECT 
            count(DISTINCT task_id) as total_tasks,
            count(*) as total_attempts,
            sum(completed) as total_completed,
            sum(first_pass_success) as total_first_pass,
            avg(CASE WHEN completed = 1 THEN input_tokens + output_tokens ELSE NULL END) as avg_tokens,
            avg(CASE WHEN completed = 1 THEN wall_clock_seconds ELSE NULL END) as avg_sec,
            avg(CASE WHEN completed = 1 THEN agent_steps ELSE NULL END) as avg_steps,
            sum(max(0, coalesce(five_hour_before_pct, 0) - coalesce(five_hour_after_pct, 0))) as sum_delta5,
            sum(max(0, coalesce(weekly_before_pct, 0) - coalesce(weekly_after_pct, 0))) as sum_deltaw
        FROM telemetry_runs
        WHERE model_id = ? AND (task_class LIKE ? OR task_class LIKE ?)
          AND run_type = 'production' AND task_id LIKE 'EXP-%'
    """, (model_id, f"Tier {tier_id}:%", f"Tier {tier_id}"))
    row = cursor.fetchone()
    if not row or not row["total_completed"] or row["total_completed"] < 3:
        # Fallback to general production runs
        cursor.execute("""
            SELECT 
                count(DISTINCT task_id) as total_tasks,
                count(*) as total_attempts,
                sum(completed) as total_completed,
                sum(first_pass_success) as total_first_pass,
                avg(CASE WHEN completed = 1 THEN input_tokens + output_tokens ELSE NULL END) as avg_tokens,
                avg(CASE WHEN completed = 1 THEN wall_clock_seconds ELSE NULL END) as avg_sec,
                avg(CASE WHEN completed = 1 THEN agent_steps ELSE NULL END) as avg_steps,
                sum(max(0, coalesce(five_hour_before_pct, 0) - coalesce(five_hour_after_pct, 0))) as sum_delta5,
                sum(max(0, coalesce(weekly_before_pct, 0) - coalesce(weekly_after_pct, 0))) as sum_deltaw
            FROM telemetry_runs
            WHERE model_id = ? AND (task_class LIKE ? OR task_class LIKE ?)
              AND run_type = 'production'
        """, (model_id, f"Tier {tier_id}:%", f"Tier {tier_id}"))
        row = cursor.fetchone()
        if not row or not row["total_completed"] or row["total_completed"] < 3:
            return None

    total_completed = float(row["total_completed"])
    total_attempts = float(row["total_attempts"] or total_completed)
    fp = min(1.0, max(0.0, float(row["total_first_pass"] or 0) / max(1.0, total_attempts)))
    att_per_done = total_attempts / total_completed

    sum_delta5 = float(row["sum_delta5"] or 0)
    sum_deltaw = float(row["sum_deltaw"] or 0)

    effective_delta = sum_delta5 if sum_delta5 > 0 else (sum_deltaw if sum_deltaw > 0 else None)
    tasks_per_1pct = (total_completed / effective_delta) if effective_delta and effective_delta > 0 else None

    return {
        "tasks_per_1pct": round(tasks_per_1pct, 2) if tasks_per_1pct else None,
        "first_pass_rate": round(fp, 3),
        "att_per_done": round(att_per_done, 2),
        "tokens_per_completed": int(row["avg_tokens"] or 0),
        "sec_per_completed": round(row["avg_sec"] or 0, 1),
        "steps_per_completed": round(row["avg_steps"] or 0, 1),
        "sample_size": int(total_completed),
        "source": "live_telemetry"
    }

from engine.cost_spec import (
    pool_economics,
    format_tasks_per_pool,
    pool_weights,
    TIER_PROFILE_TOKENS,
    DEFAULT_MIX,
    cost_per_pool as spec_cost_per_pool,
)

def recalculate_all_yields(conn=None):
    close_at_end = False
    if conn is None:
        conn = get_connection()
        close_at_end = True

    cursor = conn.cursor()

    # Pre-calculate pool weights per subscription
    cursor.execute("SELECT id, sub_id, pool_weight FROM quota_pools;")
    all_pools = cursor.fetchall()
    subs_pools = {}
    explicit_weights = {}
    for p in all_pools:
        subs_pools.setdefault(p["sub_id"], []).append(p["id"])
        if p["pool_weight"] is not None:
            explicit_weights[p["id"]] = float(p["pool_weight"])
    
    computed_weights = {}
    for sub_id, p_ids in subs_pools.items():
        sub_weights = pool_weights(p_ids, explicit_weights)
        computed_weights.update(sub_weights)

    cursor.execute("""
        SELECT m.model_id, m.display_name, m.provider, m.harness, m.pool_id,
               m.input_cost_per_m, m.output_cost_per_m, m.reasoning_effort, m.speed_mode,
               p.sub_id, p.reset_window_hours, p.window_type, p.ui_granularity_pct, s.monthly_cost
        FROM models m
        LEFT JOIN quota_pools p ON m.pool_id = p.id
        LEFT JOIN subscriptions s ON p.sub_id = s.id
    """)
    models = cursor.fetchall()

    for m in models:
        p_weight = computed_weights.get(m["pool_id"], 1.0)
        for tier_id in [1, 2, 3, 4]:
            calc = compute_model_tier_yield(m, tier_id, conn=conn, pool_weight=p_weight)
            cursor.execute("""
                INSERT OR REPLACE INTO model_task_yields (
                    model_id, tier_id, tasks_per_pool_cycle, tasks_per_month,
                    cost_per_completed_task, api_cost_per_task, success_adjusted_tokens,
                    success_adjusted_seconds, quota_first_score,
                    time_reliability_score, recommendation_notes,
                    cost_per_pool, tasks_per_pool_low, tasks_per_pool_high,
                    tasks_per_pool_evidence, api_value_per_pool, leverage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                m["model_id"], tier_id, calc["tasks_per_pool_cycle"],
                calc["tasks_per_month"], calc["cost_per_completed_task"],
                calc["api_cost_per_task"], calc["success_adjusted_tokens"],
                calc["success_adjusted_seconds"], calc["quota_first_score"],
                calc["time_reliability_score"], calc["notes"],
                calc.get("cost_per_pool"), calc.get("tasks_per_pool_low"),
                calc.get("tasks_per_pool_high"), calc.get("tasks_per_pool_evidence"),
                calc.get("api_value_per_pool"), calc.get("leverage")
            ))

    conn.commit()
    if close_at_end:
        conn.close()
    print("Recalculated yields and API benchmark costs across all models and tiers.")

def compute_model_tier_yield(model, tier_id, conn=None, pool_weight=1.0):
    m_dict = dict(model) if hasattr(model, "keys") else model
    model_id = m_dict["model_id"]
    sub_cost = m_dict["monthly_cost"] if m_dict.get("monthly_cost") is not None else 20.0
    pool_id = m_dict.get("pool_id") or ""
    window_hours = m_dict.get("reset_window_hours") or 5.0
    window_type = m_dict.get("window_type") or "rolling_5h"
    granularity = float(m_dict.get("ui_granularity_pct") or 1.0)
    spec = TIER_SPECS[tier_id]

    in_cost = float(m_dict.get("input_cost_per_m") or 0.0)
    out_cost = float(m_dict.get("output_cost_per_m") or 0.0)

    # 1. Primary: Check live empirical telemetry runs
    live_emp = get_telemetry_metrics(conn, model_id, tier_id)
    emp = None
    is_live = False
    if live_emp and live_emp.get("tasks_per_1pct"):
        emp = live_emp
        is_live = True
    elif (model_id, tier_id) in EMPIRICAL_V7:
        emp = EMPIRICAL_V7[(model_id, tier_id)]
        is_live = False

    completed = None
    attempts = None
    tokens_completed = None
    seconds = None
    weekly_delta = None
    five_hour_delta = None
    fp = 0.88 if tier_id <= 2 else 0.58

    if emp:
        fp = emp["first_pass_rate"]
        tokens_completed = float(emp["tokens_per_completed"])
        seconds = float(emp["sec_per_completed"])
        completed = float(emp.get("sample_size", 20.0))
        att_per_done = float(emp.get("att_per_done", 1.1))
        attempts = completed * att_per_done
        tasks_per_1pct = float(emp["tasks_per_1pct"])
        if tasks_per_1pct > 0:
            weekly_delta = completed / tasks_per_1pct
            five_hour_delta = weekly_delta
    else:
        # Generalized estimation tokens & seconds
        reasoning = m_dict.get("reasoning_effort") or "medium"
        if reasoning == "high":
            mult_tokens = 1.3
            mult_time = 1.5
            fp = 0.92 if tier_id <= 2 else 0.72
        elif reasoning == "low":
            mult_tokens = 0.8
            mult_time = 0.7
            fp = 0.85 if tier_id <= 2 else 0.48
        else:
            mult_tokens = 1.0
            mult_time = 1.0
            fp = 0.88 if tier_id <= 2 else 0.58

        att_per_done = 1.0 / fp if fp > 0 else 2.0
        tokens_completed = float(TIER_PROFILE_TOKENS[tier_id] * mult_tokens * att_per_done)
        seconds = round(spec["base_sec"] * mult_time * att_per_done, 1)

    # Call standardized pool_economics
    econ = pool_economics(
        tier=tier_id,
        monthly_price=sub_cost,
        pool_weight=pool_weight,
        window_type=window_type,
        input_rate=in_cost,
        output_rate=out_cost,
        speed=m_dict.get("speed_mode"),
        completed=completed,
        attempts=attempts,
        tokens_per_completed=tokens_completed,
        weekly_delta_pct=weekly_delta,
        five_hour_delta_pct=five_hour_delta,
        granularity_pct=granularity
    )

    tasks_per_pool_cycle = econ["tasks_per_pool"] or 50.0
    cycles = econ["pool_cycles_per_month"] or 4.0
    tasks_per_month = tasks_per_pool_cycle * cycles
    cost_per_task = econ["sub_cost_per_task"] if econ["sub_cost_per_task"] is not None else 0.0
    raw_api_cost = econ["api_cost_per_task"] or 0.0

    # Scores
    quota_multiplier = 5.0 if tier_id <= 3 else 15.0
    if emp:
        quota_score = min(100.0, float(emp["tasks_per_1pct"]) * quota_multiplier)
    else:
        quota_score = min(80.0, tasks_per_pool_cycle / (tier_id * 5.0))
    sec_divisor = 5.0 if tier_id <= 3 else (spec["base_sec"] / 10.0)
    time_score = max(0.0, 100.0 - (seconds / sec_divisor)) * fp

    formatted_tpp = format_tasks_per_pool(econ)
    if is_live:
        notes = f"Live telemetry (N={emp['sample_size']}): {formatted_tpp} tasks/pool, {fp*100:.0f}% 1st-pass, {seconds:.1f}s/done."
    elif emp:
        notes = f"Empirical v7 prior: {formatted_tpp} tasks/pool, {fp*100:.0f}% 1st-pass, {seconds:.1f}s/done."
    else:
        notes = f"Estimated: {formatted_tpp} tasks/pool, {fp*100:.0f}% est 1st-pass, {seconds:.1f}s/done."

    return {
        "tasks_per_pool_cycle": round(tasks_per_pool_cycle, 1),
        "tasks_per_month": round(tasks_per_month, 0),
        "cost_per_completed_task": round(cost_per_task, 4),
        "api_cost_per_task": round(raw_api_cost, 4),
        "success_adjusted_tokens": int(tokens_completed),
        "success_adjusted_seconds": round(seconds, 1),
        "quota_first_score": round(quota_score, 1),
        "time_reliability_score": round(time_score, 1),
        "notes": notes,
        "cost_per_pool": round(econ["cost_per_pool"], 4) if econ["cost_per_pool"] is not None else None,
        "tasks_per_pool_low": round(econ["tasks_per_pool_low"], 1) if econ.get("tasks_per_pool_low") is not None else None,
        "tasks_per_pool_high": round(econ["tasks_per_pool_high"], 1) if econ.get("tasks_per_pool_high") is not None else None,
        "tasks_per_pool_evidence": econ.get("tasks_per_pool_evidence"),
        "api_value_per_pool": round(econ["api_value_per_pool"], 4) if econ.get("api_value_per_pool") is not None else None,
        "leverage": round(econ["leverage"], 2) if econ.get("leverage") is not None else None,
    }

if __name__ == "__main__":
    recalculate_all_yields()
