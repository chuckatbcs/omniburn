#!/usr/bin/env python3
"""
Harness & Frontier Model Burn Rate Calculator.
Focuses on subscription burn rate, harness rate limits, and comparative capability.
"""

import json
import os

SUBS_FILE = os.path.join(os.path.dirname(__file__), "subscriptions.json")
CATALOG_FILE = os.path.join(os.path.dirname(__file__), "models_catalog.json")

def load_data():
    with open(SUBS_FILE, "r", encoding="utf-8") as f:
        subs_data = json.load(f)
    catalog = {}
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    return subs_data, catalog

def calculate_burn_rate(subs_data, catalog_data):
    subscriptions = subs_data.get("subscriptions", [])
    free_tiers = subs_data.get("free_tiers", [])

    total_monthly = sum(s.get("cost_monthly", 0) for s in subscriptions if s.get("status") == "active")
    daily_burn = round(total_monthly / 30.4375, 2)
    annual_burn = round(total_monthly * 12, 2)

    # Harness summaries
    harnesses = [
        {
            "id": "cursor",
            "name": "Cursor IDE Harness (inc. Grok Bot)",
            "sub_name": "Cursor Pro",
            "monthly_cost": 20.00,
            "daily_cost": 0.66,
            "burn_structure": "500 fast requests/mo (~$0.04/request) + unlimited slow requests + unmetered Cursor Tab autocompletes",
            "primary_models": ["Claude 3.5 Sonnet", "Grok 2 / Grok Bot", "GPT-4o"],
            "throttle_behavior": "Drops to slow queue after 500 fast requests; work is never completely blocked",
            "best_for": "Iterative coding, agentic codebase diffs, inline completions, quick Grok bot queries"
        },
        {
            "id": "chatgpt",
            "name": "ChatGPT / Codex Harness",
            "sub_name": "ChatGPT Plus",
            "monthly_cost": 20.00,
            "daily_cost": 0.66,
            "burn_structure": "Sliding window (40-80 msgs / 3 hrs on GPT-4o) + weekly quotas on o1 and o3-mini",
            "primary_models": ["o3-mini", "o1", "GPT-4o", "Canvas / Codex"],
            "throttle_behavior": "Locked out until sliding window resets or forced onto GPT-4o-mini",
            "best_for": "Deep STEM / algorithmic reasoning (o1/o3-mini), Canvas side-by-side editing, Code Interpreter Python execution, Voice"
        },
        {
            "id": "gemini",
            "name": "Antigravity & Gemini Studio Harness",
            "sub_name": "Google One AI Premium",
            "monthly_cost": 19.99,
            "daily_cost": 0.66,
            "burn_structure": "High-throughput message caps + massive 1M-2M context window ingestion ($10/mo net after 2TB storage offset)",
            "primary_models": ["Gemini 2.0 Flash", "Gemini 2.0 Pro Exp", "Gemini 1.5 Pro"],
            "throttle_behavior": "Very generous limits; rarely throttles for normal workflow",
            "best_for": "Whole-repo codebase auditing (2M tokens), multimodal video/audio parsing, agentic tool workflows in Antigravity"
        },
        {
            "id": "nous",
            "name": "NousResearch Research Portal & Discord",
            "sub_name": "Nous Free Account",
            "monthly_cost": 0.00,
            "daily_cost": 0.00,
            "burn_structure": "Free community tier access",
            "primary_models": ["Hermes 3 (405B, 70B, 8B)", "Nous Theta"],
            "throttle_behavior": "Server queue during high-traffic periods",
            "best_for": "Uncensored reasoning, open-weights benchmark evaluation, custom prompt steerability"
        },
        {
            "id": "nvidia",
            "name": "NVIDIA NIM Cloud / build.nvidia.com",
            "sub_name": "NVIDIA Developer Free Tier",
            "monthly_cost": 0.00,
            "daily_cost": 0.00,
            "burn_structure": "1,000 free API / playground credits",
            "primary_models": ["Llama 3.3 70B", "Llama 3.1 Nemotron 70B", "Mistral Large 2"],
            "throttle_behavior": "Credits balance depletion or rate limits",
            "best_for": "Hardware-optimized low-latency inference, reward modeling, self-hosted NIM testing"
        }
    ]

    frontier_models = catalog_data.get("frontier_models", [])
    # Sort by release date descending (newest first)
    frontier_models_sorted = sorted(frontier_models, key=lambda x: x.get("release_date", ""), reverse=True)

    return {
        "monthly_burn": total_monthly,
        "daily_burn": daily_burn,
        "annual_burn": annual_burn,
        "active_paid_subscriptions": len([s for s in subscriptions if s.get("status") == "active"]),
        "harnesses": harnesses,
        "frontier_models_sorted_newest": frontier_models_sorted,
        "total_frontier_models": len(frontier_models_sorted),
        "last_catalog_update": catalog_data.get("last_updated", "Recent")
    }

if __name__ == "__main__":
    subs, cat = load_data()
    summary = calculate_burn_rate(subs, cat)
    print("=== SUBSCRIPTION & HARNESS BURN RATE ===")
    print(f"Total Monthly Burn: ${summary['monthly_burn']:.2f}/mo  |  Daily: ${summary['daily_burn']:.2f}/day\n")
    print("HARNESS COMPARISON:")
    for h in summary["harnesses"]:
        print(f" • {h['name']} (${h['monthly_cost']:.2f}/mo): {h['burn_structure']}")
    print("\nFRONTIER MODELS (SORTED NEWEST FIRST):")
    for m in summary["frontier_models_sorted_newest"]:
        print(f" [{m['release_date']}] {m['name']} ({m['vendor']})")
        print(f"    Harness: {m['harness']} | Burn: {m['burn_rate_metric']}")
        print(f"    Vs Others: {m['comparative_advantage']}\n")
