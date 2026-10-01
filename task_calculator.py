#!/usr/bin/env python3
"""
Task Yield & Usage Maximization Calculator.
Calculates completed tasks per month for each model at various reasoning levels.
"""

import json

# Generalized Task Definition:
# A standard developer/knowledge task: ~2,500 prompt tokens + ~1,000 output/thinking tokens (or 1 multi-turn code fix/analysis).

TASK_MODELS = [
    {
        "plan": "Gemini Pro / Antigravity ($19.99/mo)",
        "model": "Gemini 3.8 Flash",
        "vendor": "Google",
        "reasoning_level": "Low / Direct Execution",
        "estimated_tasks_per_month": 35000,
        "tasks_per_day": 1150,
        "cost_per_task": 0.0006,
        "limiting_factor": "Generous API/UI rate ceiling (~1,500 req/day)",
        "recommended_for": "Massive batch processing, fast linting, unit test generation, repetitive code refactors",
        "efficiency_verdict": "👑 UNRIVALED VOLUME: 35,000 tasks/mo at sub-100ms latency."
    },
    {
        "plan": "Gemini Pro / Antigravity ($19.99/mo)",
        "model": "Gemini 3.8 Flash (Agentic Loops)",
        "vendor": "Google",
        "reasoning_level": "Medium (Multi-turn Tool Calling)",
        "estimated_tasks_per_month": 4500,
        "tasks_per_day": 150,
        "cost_per_task": 0.0044,
        "limiting_factor": "Multi-step tool executions (~6 calls per completed task)",
        "recommended_for": "Autonomous multi-file edits, repo navigation, shell test-and-repair loops",
        "efficiency_verdict": "Best autonomous agent throughput."
    },
    {
        "plan": "Gemini Pro / Antigravity ($19.99/mo)",
        "model": "Gemini 3.1 Pro",
        "vendor": "Google",
        "reasoning_level": "High (Deep 1M+ Context Reasoning)",
        "estimated_tasks_per_month": 2200,
        "tasks_per_day": 72,
        "cost_per_task": 0.0091,
        "limiting_factor": "Pro model rate limits (~75-100 turns/day)",
        "recommended_for": "Entire repository audits, complex architecture analysis, 1-hour media parsing",
        "efficiency_verdict": "Most completed tasks for massive-context (1M+) workloads."
    },
    {
        "plan": "ChatGPT Plus / Codex ($20.00/mo)",
        "model": "GPT-6 Luna Pro",
        "vendor": "OpenAI",
        "reasoning_level": "Low / Fast Omni",
        "estimated_tasks_per_month": 2100,
        "tasks_per_day": 70,
        "cost_per_task": 0.0095,
        "limiting_factor": "Sliding window of 40-80 msgs / 3 hours (~70 msgs/workday)",
        "recommended_for": "Quick questions, voice interaction, basic script generation, simple diffs",
        "efficiency_verdict": "Highest task volume inside ChatGPT Plus."
    },
    {
        "plan": "Cursor Pro ($20.00/mo)",
        "model": "Grok 4.7 / Claude Opus 5.5 (Slow Queue)",
        "vendor": "xAI / Anthropic (Cursor)",
        "reasoning_level": "Medium (Iterative Code Diffs)",
        "estimated_tasks_per_month": 1600,
        "tasks_per_day": 53,
        "cost_per_task": 0.0125,
        "limiting_factor": "Standard queue latency during peak hours (no hard cutoff)",
        "recommended_for": "All-day coding sessions after exhausting the 500 fast request pool",
        "efficiency_verdict": "Zero lockout safety net: keeps producing code indefinitely."
    },
    {
        "plan": "NVIDIA NIM (Free Tier - $0/mo)",
        "model": "Nemotron 3.5 Lightning (Free Tier)",
        "vendor": "NVIDIA",
        "reasoning_level": "Medium / TensorRT Accelerated",
        "estimated_tasks_per_month": 1500,
        "tasks_per_day": 50,
        "cost_per_task": 0.0000,
        "limiting_factor": "1,000 free monthly credits / rate-limited endpoints",
        "recommended_for": "Offloading fast completions and synthetic data testing at $0 cost",
        "efficiency_verdict": "Best free tier yield: 1,500 free completed tasks."
    },
    {
        "plan": "ChatGPT Plus / Codex ($20.00/mo)",
        "model": "GPT-6 Sol Pro / o3-mini",
        "vendor": "OpenAI",
        "reasoning_level": "Low Effort Reasoning",
        "estimated_tasks_per_month": 1200,
        "tasks_per_day": 40,
        "cost_per_task": 0.0167,
        "limiting_factor": "Rolling window message cap (minimal thinking token burn)",
        "recommended_for": "Standard algorithms, competitive coding challenges, unit test writing",
        "efficiency_verdict": "Sweet spot for OpenAI reasoning tasks without burning quotas."
    },
    {
        "plan": "ChatGPT Plus / Codex ($20.00/mo)",
        "model": "GPT-6 Sol Pro / o3-mini",
        "vendor": "OpenAI",
        "reasoning_level": "Medium Effort Reasoning",
        "estimated_tasks_per_month": 600,
        "tasks_per_day": 20,
        "cost_per_task": 0.0333,
        "limiting_factor": "Time window + higher thinking token consumption (~20 tasks/day)",
        "recommended_for": "Non-trivial bug diagnosis, API contract designs, architectural validation",
        "efficiency_verdict": "Balanced quality/speed for complex problem solving."
    },
    {
        "plan": "Cursor Pro ($20.00/mo)",
        "model": "Claude Opus 5.5 / Grok 4.7 (Fast Pool)",
        "vendor": "Anthropic / xAI",
        "reasoning_level": "Medium / Frontier Coding",
        "estimated_tasks_per_month": 500,
        "tasks_per_day": 16.6,
        "cost_per_task": 0.0400,
        "limiting_factor": "Hard monthly allowance of 500 Fast Premium Requests",
        "recommended_for": "High-leverage Composer refactoring, multi-file diffs, urgent reviews",
        "efficiency_verdict": "Highest quality per task in code editor before slow fallback."
    },
    {
        "plan": "NousResearch (Free Account - $0/mo)",
        "model": "Hermes 4 (405B Flagship)",
        "vendor": "Nous Research",
        "reasoning_level": "High (405B Frontier Open Weights)",
        "estimated_tasks_per_month": 450,
        "tasks_per_day": 15,
        "cost_per_task": 0.0000,
        "limiting_factor": "Community portal queues during peak hours",
        "recommended_for": "Uncensored logic, synthetic dataset evaluation, custom prompt steerability",
        "efficiency_verdict": "450 free tasks on a flagship 405B model."
    },
    {
        "plan": "ChatGPT Plus / Codex ($20.00/mo)",
        "model": "GPT-6 Sol Pro / o3-mini",
        "vendor": "OpenAI",
        "reasoning_level": "High Effort Reasoning",
        "estimated_tasks_per_month": 280,
        "tasks_per_day": 9.3,
        "cost_per_task": 0.0714,
        "limiting_factor": "Throttling: thinking tokens consume significant rolling quota",
        "recommended_for": "Extremely convoluted bugs, distributed system invariants, security proofs",
        "efficiency_verdict": "Low task volume, but solves problems requiring 50+ lines of internal thought."
    },
    {
        "plan": "ChatGPT Plus / Codex ($20.00/mo)",
        "model": "GPT-6 Astra Pro",
        "vendor": "OpenAI",
        "reasoning_level": "Max / Deliberative Flagship",
        "estimated_tasks_per_month": 150,
        "tasks_per_day": 5,
        "cost_per_task": 0.1333,
        "limiting_factor": "Strict weekly quota (~35-40 queries/week total)",
        "recommended_for": "PhD-level mathematical breakthroughs, complex legal/policy proofs, novel algorithms",
        "efficiency_verdict": "Lowest task volume (only ~5 tasks/day), but maximum intelligence ceiling."
    },
    {
        "plan": "Cursor Pro ($20.00/mo)",
        "model": "Multi-Agent Composer Loop (Opus 5.5)",
        "vendor": "Anthropic (Cursor)",
        "reasoning_level": "High (Multi-File Agent Orchestration)",
        "estimated_tasks_per_month": 125,
        "tasks_per_day": 4.1,
        "cost_per_task": 0.1600,
        "limiting_factor": "Consumes 3-5 fast requests per end-to-end multi-file agent task",
        "recommended_for": "Complete end-to-end feature implementations spanning 10+ files",
        "efficiency_verdict": "Fewer completed tasks, but each task replaces hours of manual coding."
    }
]

def print_table():
    print("=" * 115)
    print(f"{'PLAN':<32} | {'MODEL & REASONING LEVEL':<35} | {'TASKS/MO':<9} | {'TASKS/DAY':<9} | {'UNIT COST'}")
    print("=" * 115)
    for m in TASK_MODELS:
        model_str = f"{m['model']} ({m['reasoning_level'].split()[0]})"
        print(f"{m['plan']:<32} | {model_str:<35} | {m['estimated_tasks_per_month']:<9,} | {m['tasks_per_day']:<9.1f} | ${m['cost_per_task']:.4f}")
    print("=" * 115)

if __name__ == "__main__":
    print_table()
