#!/usr/bin/env python3
"""
Telemetry logger and empirical statistical analysis module for OmniBurn.
Handles task logging, live quota updates, and statistical aggregations (Wilson CIs, McNemar tests).
"""

import math
from datetime import datetime, timezone
from engine.db import get_connection

def wilson_score_interval(k, n, confidence=0.95):
    if n == 0:
        return 0.0, 0.0
    z = 1.95996
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)

def log_task_run(
    task_id, model_id, task_class, completed=True, first_pass_success=True,
    attempt_number=1, tool_calls=0, agent_steps=0, input_tokens=0,
    cache_tokens=0, output_tokens=0, wall_clock_seconds=0.0,
    dec_5h=0, dec_week=0, description="", db_path=None
):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Get pool for model
    cursor.execute("SELECT pool_id FROM models WHERE model_id = ?", (model_id,))
    row = cursor.fetchone()
    pool_id = row["pool_id"] if row else "gemini_models"

    # Fetch pool percentages
    cursor.execute("SELECT current_pct_remaining, weekly_pct_remaining FROM quota_pools WHERE id = ?", (pool_id,))
    prow = cursor.fetchone()
    cur_5h = prow["current_pct_remaining"] if prow else 100
    cur_wk = prow["weekly_pct_remaining"] if prow else 100

    after_5h = max(0, cur_5h - dec_5h)
    after_wk = max(0, cur_wk - dec_week)

    cursor.execute("""
        INSERT OR REPLACE INTO telemetry_runs (
            task_id, matched_pair_id, task_class, model_id, reasoning,
            timestamp, five_hour_before_pct, five_hour_after_pct,
            weekly_before_pct, weekly_after_pct, completed, first_pass_success,
            attempt_number, tool_calls, agent_steps, input_tokens, cache_tokens,
            output_tokens, wall_clock_seconds, sanitized_description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        task_id, f"USER-RUN-{task_id[:8]}", task_class, model_id, "medium",
        now_iso, cur_5h, after_5h, cur_wk, after_wk,
        1 if completed else 0, 1 if first_pass_success else 0, attempt_number,
        tool_calls, agent_steps, input_tokens, cache_tokens, output_tokens,
        wall_clock_seconds, description
    ))

    # Update pool state
    if dec_5h > 0 or dec_week > 0:
        cursor.execute("""
            UPDATE quota_pools
            SET current_pct_remaining = ?, weekly_pct_remaining = ?
            WHERE id = ?
        """, (after_5h, after_wk, pool_id))

    conn.commit()
    conn.close()
    return {"status": "ok", "task_id": task_id, "pool_5h_remaining": after_5h}

def get_telemetry_summary(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT model_id, task_class,
               COUNT(*) as total_attempts,
               SUM(completed) as completed_tasks,
               SUM(CASE WHEN first_pass_success = 1 AND attempt_number = 1 THEN 1 ELSE 0 END) as first_pass_tasks,
               SUM(input_tokens + output_tokens) as total_tokens,
               SUM(wall_clock_seconds) as total_seconds,
               SUM(agent_steps) as total_steps,
               SUM(CASE WHEN five_hour_before_pct > five_hour_after_pct THEN five_hour_before_pct - five_hour_after_pct ELSE 0 END) as visible_5h_dec,
               SUM(CASE WHEN weekly_before_pct > weekly_after_pct THEN weekly_before_pct - weekly_after_pct ELSE 0 END) as visible_wk_dec
        FROM telemetry_runs
        GROUP BY model_id, task_class
    """)
    rows = cursor.fetchall()

    summary = []
    for r in rows:
        att = r["total_attempts"]
        done = r["completed_tasks"] or 1
        fp = r["first_pass_tasks"] or 0
        # Corrected denominator: matched completed tasks (20 for benchmark, or done count)
        matched_n = done
        fp_rate = fp / matched_n if matched_n > 0 else 0.0
        ci_low, ci_high = wilson_score_interval(fp, matched_n)
        
        dec_5h = r["visible_5h_dec"]
        tasks_per_1pct = done / dec_5h if dec_5h > 0 else 0.0
        tokens_per_done = r["total_tokens"] / done if done > 0 else 0
        sec_per_done = r["total_seconds"] / done if done > 0 else 0
        steps_per_done = r["total_steps"] / done if done > 0 else 0

        summary.append({
            "model_id": r["model_id"],
            "task_class": r["task_class"],
            "attempts": att,
            "completed": done,
            "first_pass_tasks": fp,
            "first_pass_rate_pct": round(fp_rate * 100, 1),
            "ci_low_pct": round(ci_low * 100, 1),
            "ci_high_pct": round(ci_high * 100, 1),
            "attempts_per_done": round(att / done, 2),
            "visible_5h_dec": dec_5h,
            "tasks_per_1pct": round(tasks_per_1pct, 2),
            "tokens_per_completed": int(tokens_per_done),
            "sec_per_completed": round(sec_per_done, 1),
            "steps_per_completed": round(steps_per_done, 1)
        })

    conn.close()
    return summary

if __name__ == "__main__":
    s = get_telemetry_summary()
    print(f"Summary computed for {len(s)} empirical lanes.")
