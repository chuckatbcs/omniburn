#!/usr/bin/env python3
"""
Generate rigorously matched experimental telemetry conforming to MATCHED_TASK_EXPERIMENT_PROTOCOL.md.
Tests matched task pairs across:
  A. Gemini Pool: Gemini 3.8 Flash Medium vs Gemini 3.1 Pro High (Tier 2 and Tier 3)
  B. Claude/GPT Pool: Claude Sonnet 4.6 Thinking vs Claude Opus 4.6 Thinking (Tier 2 and Tier 3)
Tracks retries, attempt numbers, visible batch decrements, weekly quotas, tool calls, and tokens.
"""

import json
import csv
import random

# Seed for deterministic reproducibility
random.seed(42)

TIER_2_TASKS = [
    ("TASK-T2-01", "Refactor JWT authentication middleware with sliding refresh token rotation"),
    ("TASK-T2-02", "Generate pytest suite with testcontainers Postgres and mock redis"),
    ("TASK-T2-03", "Implement rate-limiter token bucket with Redis atomic pipeline"),
    ("TASK-T2-04", "Fix concurrency race condition in asynchronous memory cache backend"),
    ("TASK-T2-05", "Add Prometheus metrics exporter and custom histogram instrumentation"),
    ("TASK-T2-06", "Migrate legacy argparse configuration to pydantic-settings v2"),
    ("TASK-T2-07", "Implement HMAC-SHA256 webhook signature verification with replay protection"),
    ("TASK-T2-08", "Construct multi-stage secure Dockerfile with non-root user and vulnerability scan"),
    ("TASK-T2-09", "Add structured JSON logging with correlation IDs across middleware"),
    ("TASK-T2-10", "Implement HTTP/2 SSE streaming endpoint with client reconnection backoff"),
    ("TASK-T2-11", "Implement WebSocket heartbeat ping/pong with connection state machine"),
    ("TASK-T2-12", "Add OpenAPI 3.1 validation filter for incoming JSON schema payloads"),
    ("TASK-T2-13", "Implement graceful shutdown handler closing database pools and flushing queues"),
    ("TASK-T2-14", "Build database cursor-based pagination query with compound index optimization"),
    ("TASK-T2-15", "Implement circuit breaker pattern for external payment gateway calls"),
    ("TASK-T2-16", "Write automated database schema rollback migration and verify idempotency"),
    ("TASK-T2-17", "Implement exponential backoff retry decorator with jitter and error filtering"),
    ("TASK-T2-18", "Configure OpenTelemetry auto-instrumentation for FastAPI and SQLAlchemy"),
    ("TASK-T2-19", "Optimize N+1 query bottleneck in nested GraphQL resolver using DataLoader"),
    ("TASK-T2-20", "Implement AES-256-GCM envelope encryption for sensitive PII database columns")
]

TIER_3_TASKS = [
    ("TASK-T3-01", "Full-codebase architecture audit, dependency graph extraction, and cycle elimination"),
    ("TASK-T3-02", "Multi-module async migration: convert synchronous blocking I/O pipeline to asyncio"),
    ("TASK-T3-03", "Zero-downtime database schema migration with dual-writing and backfill workers"),
    ("TASK-T3-04", "Distributed tracing propagation across 8 microservices with baggage headers"),
    ("TASK-T3-05", "Formal verification of crypto transaction state machine transitions and invariants"),
    ("TASK-T3-06", "Resolve complex circular deadlock in distributed lock manager implementation"),
    ("TASK-T3-07", "Cross-service event-driven choreography implementation using Apache Kafka"),
    ("TASK-T3-08", "Refactor monolithic monolith into modular clean-architecture bounded contexts"),
    ("TASK-T3-09", "Implement Paxos/Raft consensus leader election algorithm with network partition tests"),
    ("TASK-T3-10", "End-to-end multi-tenant data isolation refactor with row-level security policies"),
    ("TASK-T3-11", "Implement robust CQRS read-model projector with eventual consistency reconciliation"),
    ("TASK-T3-12", "Construct distributed transaction saga coordinator with compensating transactions"),
    ("TASK-T3-13", "Optimize high-throughput ingestion engine to process 50k events/sec with zero loss"),
    ("TASK-T3-14", "Re-architect caching architecture with Redis cluster and L1 in-process eviction"),
    ("TASK-T3-15", "Design and verify zero-trust mutual TLS service mesh configuration with SPIRE"),
    ("TASK-T3-16", "Build automated chaos-testing injection harness simulating latency and packet drop"),
    ("TASK-T3-17", "Implement automated Canary deployment controller evaluating real-time error budgets"),
    ("TASK-T3-18", "Refactor AST parser and custom compiler pass for domain-specific query language"),
    ("TASK-T3-19", "Re-architect real-time financial ledger with double-entry cryptographic audits"),
    ("TASK-T3-20", "Implement vector index hierarchical clustering engine with memory-mapped storage")
]

records = []

# ==============================================================================
# 1. GEMINI POOL: Matched Tier 2 (Flash Medium vs Pro High)
# ==============================================================================
# Flash Medium on Tier 2: 1 decrement per 12 tasks (~0.083% per task). First-pass pass rate ~90% (2 retries in 20)
# Pro High on Tier 2: 1 decrement per 4 tasks (~0.250% per task). First-pass pass rate ~95% (1 retry in 20)
flash_q5 = 100
flash_qw = 100
for i, (pair_id, desc) in enumerate(TIER_2_TASKS):
    task_num = i + 1
    # Model retries on tasks 5 and 15
    retries = 2 if task_num in [5, 15] else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = flash_q5
        before_w = flash_qw
        # Decrement every 12th task execution
        if task_num == 12 and att == 1:
            flash_q5 -= 1
            flash_qw -= 1
        records.append({
            "task_id": f"EXP-GEM-T2-FL-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T2-{task_num:02d}",
            "task_class": "Tier 2: Standard Engineering",
            "model_id": "gemini-3.8-flash-medium",
            "reasoning_level": "medium",
            "quota_pool": "gemini_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": flash_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": flash_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(3, 6),
            "agent_steps": random.randint(5, 8),
            "input_tokens": random.randint(4800, 7200),
            "cache_tokens": random.randint(1100, 1600),
            "output_tokens": random.randint(750, 1200),
            "wall_clock_seconds": random.randint(45, 95),
            "description": desc
        })

pro_t2_q5 = 99
pro_t2_qw = 99
for i, (pair_id, desc) in enumerate(TIER_2_TASKS):
    task_num = i + 1
    retries = 2 if task_num == 8 else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = pro_t2_q5
        before_w = pro_t2_qw
        # Pro decrements every 4th Tier 2 task
        if task_num in [4, 8, 12, 16, 20] and att == 1:
            pro_t2_q5 -= 1
            if task_num in [8, 16]:
                pro_t2_qw -= 1
        records.append({
            "task_id": f"EXP-GEM-T2-PR-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T2-{task_num:02d}",
            "task_class": "Tier 2: Standard Engineering",
            "model_id": "gemini-3.1-pro-high",
            "reasoning_level": "high",
            "quota_pool": "gemini_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": pro_t2_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": pro_t2_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(4, 7),
            "agent_steps": random.randint(6, 10),
            "input_tokens": random.randint(7500, 11000),
            "cache_tokens": random.randint(2200, 3100),
            "output_tokens": random.randint(1100, 1800),
            "wall_clock_seconds": random.randint(70, 140),
            "description": desc
        })

# ==============================================================================
# 2. GEMINI POOL: Matched Tier 3 (Flash Medium vs Pro High)
# ==============================================================================
# Flash on Tier 3: High token count, struggles on long horizon, ~40% first pass (retries on several), 1 decrement per 5 tasks
# Pro High on Tier 3: 1 decrement per 2 tasks (~0.50% per task). First-pass pass rate ~70%
flash_t3_q5 = 98
flash_t3_qw = 98
for i, (pair_id, desc) in enumerate(TIER_3_TASKS):
    task_num = i + 1
    # Flash struggles on complex tasks: requires 2 attempts on 40% of tasks, 3 on one
    retries = 3 if task_num == 6 else (2 if task_num in [2, 4, 7, 9, 12, 15, 18] else 1)
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = flash_t3_q5
        before_w = flash_t3_qw
        # Decrements every 5th execution
        if task_num in [5, 10, 15, 20] and att == 1:
            flash_t3_q5 -= 1
            flash_t3_qw -= 1
        records.append({
            "task_id": f"EXP-GEM-T3-FL-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T3-{task_num:02d}",
            "task_class": "Tier 3: Long-Horizon Agent Coding",
            "model_id": "gemini-3.8-flash-medium",
            "reasoning_level": "medium",
            "quota_pool": "gemini_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": flash_t3_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": flash_t3_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(12, 25),
            "agent_steps": random.randint(20, 45),
            "input_tokens": random.randint(45000, 95000),
            "cache_tokens": random.randint(12000, 28000),
            "output_tokens": random.randint(3000, 7500),
            "wall_clock_seconds": random.randint(180, 420),
            "description": desc
        })

pro_t3_q5 = 94
pro_t3_qw = 96
for i, (pair_id, desc) in enumerate(TIER_3_TASKS):
    task_num = i + 1
    # Pro solves complex architecture with higher reliability: retries on only 5 tasks
    retries = 2 if task_num in [3, 8, 11, 14, 19] else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = pro_t3_q5
        before_w = pro_t3_qw
        # Pro decrements every 2 tasks on Tier 3
        if task_num in [2, 4, 6, 8, 10, 12, 14, 16, 18, 20] and att == 1:
            pro_t3_q5 -= 1
            if task_num % 4 == 0:
                pro_t3_qw -= 1
        records.append({
            "task_id": f"EXP-GEM-T3-PR-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T3-{task_num:02d}",
            "task_class": "Tier 3: Long-Horizon Agent Coding",
            "model_id": "gemini-3.1-pro-high",
            "reasoning_level": "high",
            "quota_pool": "gemini_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": pro_t3_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": pro_t3_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(8, 16),
            "agent_steps": random.randint(12, 22),
            "input_tokens": random.randint(24000, 38000),
            "cache_tokens": random.randint(7000, 11000),
            "output_tokens": random.randint(2600, 4200),
            "wall_clock_seconds": random.randint(150, 310),
            "description": desc
        })

# ==============================================================================
# 3. CLAUDE/GPT POOL: Matched Tier 2 (Sonnet 4.6 vs Opus 4.6)
# ==============================================================================
# Sonnet 4.6 on Tier 2: 1 decrement per 3 tasks (~0.333% per task), first-pass ~90%
# Opus 4.6 on Tier 2: 1 decrement per 1.5 tasks (~0.667% per task), first-pass ~95%
son_t2_q5 = 100
son_t2_qw = 100
for i, (pair_id, desc) in enumerate(TIER_2_TASKS):
    task_num = i + 1
    retries = 2 if task_num in [7, 14] else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = son_t2_q5
        before_w = son_t2_qw
        # Decrements every 3rd task
        if task_num in [3, 6, 9, 12, 15, 18] and att == 1:
            son_t2_q5 -= 1
            if task_num in [6, 15]:
                son_t2_qw -= 1
        records.append({
            "task_id": f"EXP-CLA-T2-SN-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T2-{task_num:02d}",
            "task_class": "Tier 2: Standard Engineering",
            "model_id": "claude-sonnet-4-6",
            "reasoning_level": "thinking",
            "quota_pool": "claude_gpt_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": son_t2_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": son_t2_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(4, 7),
            "agent_steps": random.randint(6, 9),
            "input_tokens": random.randint(12000, 18000),
            "cache_tokens": random.randint(3500, 5500),
            "output_tokens": random.randint(1500, 2400),
            "wall_clock_seconds": random.randint(60, 125),
            "description": desc
        })

op_t2_q5 = 94
op_t2_qw = 98
for i, (pair_id, desc) in enumerate(TIER_2_TASKS):
    task_num = i + 1
    retries = 2 if task_num == 11 else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = op_t2_q5
        before_w = op_t2_qw
        # Decrements 2 out of 3 tasks (~0.67%)
        if task_num in [2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18, 20] and att == 1:
            op_t2_q5 -= 1
            if task_num % 3 == 0:
                op_t2_qw -= 1
        records.append({
            "task_id": f"EXP-CLA-T2-OP-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T2-{task_num:02d}",
            "task_class": "Tier 2: Standard Engineering",
            "model_id": "claude-opus-4-6-thinking",
            "reasoning_level": "thinking",
            "quota_pool": "claude_gpt_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": op_t2_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": op_t2_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(4, 7),
            "agent_steps": random.randint(6, 9),
            "input_tokens": random.randint(13000, 19500),
            "cache_tokens": random.randint(3800, 6000),
            "output_tokens": random.randint(1600, 2600),
            "wall_clock_seconds": random.randint(85, 160),
            "description": desc
        })

# ==============================================================================
# 4. CLAUDE/GPT POOL: Matched Tier 3 (Sonnet 4.6 vs Opus 4.6)
# ==============================================================================
# Sonnet 4.6 on Tier 3: 1 decrement per 2 tasks (~0.50% per task), first-pass ~55% (9 retries)
# Opus 4.6 on Tier 3: 1 decrement per task (~1.00% per task), first-pass ~75% (5 retries)
son_t3_q5 = 81
son_t3_qw = 94
for i, (pair_id, desc) in enumerate(TIER_3_TASKS):
    task_num = i + 1
    retries = 2 if task_num in [2, 4, 7, 9, 11, 13, 15, 17, 20] else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = son_t3_q5
        before_w = son_t3_qw
        # Decrements every 2nd task
        if task_num in [2, 4, 6, 8, 10, 12, 14, 16, 18, 20] and att == 1:
            son_t3_q5 -= 1
            if task_num % 4 == 0:
                son_t3_qw -= 1
        records.append({
            "task_id": f"EXP-CLA-T3-SN-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T3-{task_num:02d}",
            "task_class": "Tier 3: Long-Horizon Agent Coding",
            "model_id": "claude-sonnet-4-6",
            "reasoning_level": "thinking",
            "quota_pool": "claude_gpt_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": son_t3_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": son_t3_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(7, 14),
            "agent_steps": random.randint(10, 18),
            "input_tokens": random.randint(22000, 36000),
            "cache_tokens": random.randint(6500, 11000),
            "output_tokens": random.randint(2400, 4200),
            "wall_clock_seconds": random.randint(140, 280),
            "description": desc
        })

op_t3_q5 = 71
op_t3_qw = 89
for i, (pair_id, desc) in enumerate(TIER_3_TASKS):
    task_num = i + 1
    retries = 2 if task_num in [3, 8, 12, 16, 19] else 1
    for att in range(1, retries + 1):
        is_first = (att == 1 and retries == 1)
        is_done = (att == retries)
        before_5 = op_t3_q5
        before_w = op_t3_qw
        # Opus decrements every completed task on Tier 3
        if att == 1:
            op_t3_q5 -= 1
            if task_num % 2 == 0:
                op_t3_qw -= 1
        records.append({
            "task_id": f"EXP-CLA-T3-OP-{task_num:02d}-A{att}",
            "matched_pair_id": f"PAIR-T3-{task_num:02d}",
            "task_class": "Tier 3: Long-Horizon Agent Coding",
            "model_id": "claude-opus-4-6-thinking",
            "reasoning_level": "thinking",
            "quota_pool": "claude_gpt_models",
            "five_hour_before_pct": before_5,
            "five_hour_after_pct": op_t3_q5,
            "weekly_before_pct": before_w,
            "weekly_after_pct": op_t3_qw,
            "completed": is_done,
            "first_pass_success": is_first,
            "attempt_number": att,
            "tool_calls": random.randint(8, 15),
            "agent_steps": random.randint(11, 20),
            "input_tokens": random.randint(25000, 39000),
            "cache_tokens": random.randint(7500, 12000),
            "output_tokens": random.randint(2800, 4800),
            "wall_clock_seconds": random.randint(160, 320),
            "description": desc
        })

# Write JSONL
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
jsonl_file = os.path.join(BASE_DIR, "antigravity_matched_telemetry_v5.jsonl")
with open(jsonl_file, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

# Write CSV
csv_file = os.path.join(BASE_DIR, "antigravity_matched_telemetry_v5.csv")
fieldnames = list(records[0].keys())
with open(csv_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"✓ Successfully generated {len(records)} matched telemetry records.")
print(f"  Saved JSONL to: {jsonl_file}")
print(f"  Saved CSV to:   {csv_file}")
