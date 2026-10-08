"""Regenerate tests/cost_spec_vectors.json from engine/cost_spec.py (run from the OmniBurn repo root)."""
import json, os, sys
sys.path.insert(0, os.getcwd())
from engine.cost_spec import pool_economics, pool_weights

CASES = [
    {"name": "antigravity_gemini_flash_t2_measured", "tier": 2, "monthly_price": 19.99, "pool_weight": 0.5, "window_type": "5h + weekly",
     "input_rate": 0.75, "output_rate": 3.5, "cache_rate": 0.075, "completed": 20, "attempts": 22, "tokens_per_completed": 7682.5,
     "weekly_delta_pct": 1.0, "five_hour_delta_pct": 1.0},
    {"name": "antigravity_opus_t3_measured", "tier": 3, "monthly_price": 19.99, "pool_weight": 0.5, "window_type": "rolling_5h",
     "input_rate": 5.0, "output_rate": 25.0, "cache_rate": 0.5, "completed": 20, "attempts": 25, "tokens_per_completed": 44112.65,
     "weekly_delta_pct": 10.0, "five_hour_delta_pct": 20.0},
    {"name": "antigravity_unmeasured_calibrated", "tier": 2, "monthly_price": 19.99, "pool_weight": 0.5, "window_type": "5h + weekly",
     "input_rate": 3.0, "output_rate": 15.0, "pool_budget": 150.0},
    {"name": "antigravity_unmeasured_prior", "tier": 2, "monthly_price": 19.99, "pool_weight": 0.5, "window_type": "5h + weekly",
     "input_rate": 3.0, "output_rate": 15.0},
    {"name": "cursor_composer_t2_allowance", "tier": 2, "monthly_price": 20.0, "pool_weight": 0.5, "window_type": "monthly",
     "input_rate": 0.5, "output_rate": 2.5, "cache_rate": 0.2},
    {"name": "cursor_haiku_fast_t1_allowance", "tier": 1, "monthly_price": 20.0, "pool_weight": 0.5, "window_type": "monthly_billing",
     "input_rate": 1.0, "output_rate": 5.0, "speed": "fast"},
    {"name": "chatgpt_5h_quantized_5pct", "tier": 2, "monthly_price": 20.0, "pool_weight": 1.0, "window_type": "5h + possible weekly",
     "input_rate": 2.0, "output_rate": 10.0, "completed": 10, "weekly_delta_pct": 5.0, "granularity_pct": 5.0},
    {"name": "local_unmetered", "tier": 2, "monthly_price": 0.0, "pool_weight": 1.0, "window_type": "unmetered",
     "input_rate": 0.0, "output_rate": 0.0},
    {"name": "long_context_t4_multiplier", "tier": 4, "monthly_price": 20.0, "pool_weight": 1.0, "window_type": "rolling_5h",
     "input_rate": 2.0, "output_rate": 10.0, "cache_rate": 0.1, "long_context_multipliers": {"input": 2.0, "cache_read": 2.0, "output": 1.5}},
]

WEIGHT_CASES = [
    {"name": "equal_split_two", "pool_ids": ["a", "b"], "explicit": {}},
    {"name": "explicit_one_of_three", "pool_ids": ["a", "b", "c"], "explicit": {"a": 0.5}},
]

out = {"cases": [], "weights": []}
for c in CASES:
    args = {k: v for k, v in c.items() if k != "name"}
    out["cases"].append({"name": c["name"], "input": args, "expected": pool_economics(**args)})
for w in WEIGHT_CASES:
    out["weights"].append({**w, "expected": pool_weights(w["pool_ids"], w["explicit"])})
path = os.path.join("tests", "cost_spec_vectors.json")
with open(path, "w") as f:
    json.dump(out, f, indent=2, sort_keys=True)
print(f"wrote {path}: {len(out['cases'])} cases")
