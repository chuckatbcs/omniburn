#!/usr/bin/env python3
"""
Dual-routing recommendation engine for OmniBurn.
Implements consensus v7 dual-routing strategies:
- 'quota_first': Maximize completed tasks per visible quota decrement.
- 'time_reliability_first': Minimize developer wait time, retries, and token bloat.
Filters out disabled models (is_active = 0) and disabled subscriptions/providers.
"""

from engine.db import get_connection

def _canonical_family(model_id: str, display_name: str) -> str:
    text = f"{display_name} {model_id}".lower()
    if "haiku" in text:
        return "claude-haiku"
    if "cursor-small" in text or "cursor small" in text:
        return "cursor-small"
    if "grok" in text:
        return "xai-grok"
    if "opus" in text:
        return "claude-opus"
    if "sonnet" in text:
        return "claude-sonnet"
    if "fable" in text:
        return "claude-fable"
    if "gemini" in text and "flash" in text:
        return "gemini-flash"
    if "gemini" in text and "pro" in text:
        return "gemini-pro"
    if "composer" in text:
        return "cursor-composer"
    if "astra" in text:
        return "gpt-astra"
    if "sol" in text:
        return "gpt-sol"
    if "terra" in text:
        return "gpt-terra"
    if "luna" in text:
        return "gpt-luna"
    if "deepseek" in text and ("r1" in text or "reasoner" in text):
        return "deepseek-reasoner"
    if "deepseek" in text:
        return "deepseek-chat"
    if "codestral" in text:
        return "mistral-codestral"
    if "mistral" in text:
        return "mistral-large"
    if "qwen" in text:
        return "qwen-coder"
    if "o1" in text:
        return "openai-o1"
    if "o3" in text:
        return "openai-o3"
    if "gpt-4o" in text:
        return "gpt-4o"
    if "nemotron" in text:
        return "nvidia-nemotron"
    if "hermes" in text:
        return "nous-hermes"
    if "gpt-oss" in text:
        return "gpt-oss"
    return model_id


# Capability gating per workload tier:
# Tier 1 (Micro-Task / Syntax / Short): Fast, lightweight, budget models.
# Tier 2 (Standard Engineering / Unit tests / Focused): Generalist coding models and workhorses.
# Tier 3 (Long-Horizon Multi-file Feature): Deep reasoning, long-context engineering models.
# Tier 4 (Heavy Agentic / Repo-Scale Architecture / Massive Context): Strictly frontier agentic and deliberative models.
TIER_CAPABILITY_GATES = {
    1: {"claude-haiku", "gemini-flash", "cursor-composer", "cursor-small", "gpt-luna", "gpt-terra", "openai-o3", "claude-sonnet", "gpt-oss", "gemini-pro", "gpt-sol", "deepseek-chat", "mistral-codestral", "qwen-coder", "gpt-4o"},
    2: {"claude-haiku", "gemini-flash", "cursor-composer", "gpt-terra", "gpt-luna", "gpt-sol", "claude-sonnet", "gemini-pro", "xai-grok", "gpt-astra", "claude-opus", "deepseek-chat", "deepseek-reasoner", "mistral-codestral", "mistral-large", "qwen-coder", "openai-o1", "openai-o3", "gpt-4o"},
    3: {"claude-sonnet", "gemini-pro", "gpt-sol", "xai-grok", "claude-opus", "claude-fable", "gpt-astra", "deepseek-reasoner", "openai-o1", "mistral-large"},
    4: {"claude-opus", "gpt-astra", "claude-fable", "gemini-pro", "gpt-sol", "deepseek-reasoner", "openai-o1"},
}


def recommend(tier_id=2, strategy="quota_first", plan_filter=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT m.model_id, m.display_name, m.provider, m.harness, m.pool_id,
               m.reasoning_effort, m.speed_mode, m.is_frontier,
               p.sub_id, p.pool_name, s.name as sub_name, s.monthly_cost, s.status as sub_status,
               y.tasks_per_pool_cycle, y.tasks_per_month, y.cost_per_completed_task,
               y.api_cost_per_task, y.cost_per_pool, y.tasks_per_pool_low, y.tasks_per_pool_high,
               y.tasks_per_pool_evidence, y.api_value_per_pool, y.leverage,
               y.success_adjusted_tokens, y.success_adjusted_seconds,
               y.quota_first_score, y.time_reliability_score, y.recommendation_notes
        FROM model_task_yields y
        JOIN models m ON y.model_id = m.model_id
        LEFT JOIN quota_pools p ON m.pool_id = p.id
        LEFT JOIN subscriptions s ON p.sub_id = s.id
        WHERE y.tier_id = ? AND m.is_active = 1 AND (s.status = 'active' OR s.status IS NULL)
    """
    params = [tier_id]
    if plan_filter and plan_filter != "all":
        query += " AND (s.id LIKE ? OR p.id LIKE ?)"
        params.extend([f"%{plan_filter}%", f"%{plan_filter}%"])

    if strategy == "quota_first":
        query += " ORDER BY y.quota_first_score DESC, y.tasks_per_pool_cycle DESC, m.is_frontier DESC, m.display_name DESC"
    else:
        query += " ORDER BY y.time_reliability_score DESC, y.success_adjusted_seconds ASC, m.is_frontier DESC, m.display_name DESC"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    gate = TIER_CAPABILITY_GATES.get(tier_id)
    if gate:
        rows = [r for r in rows if _canonical_family(r["model_id"], r["display_name"]) in gate]

    if not rows:
        return {
            "tier_id": tier_id,
            "strategy": strategy,
            "error": "No active models available for this criteria. All candidate models or providers are disabled.",
            "top_recommendation": None,
            "runner_up": None,
            "rationale": ["All candidate models are currently disabled in this tier. Please enable at least one model or provider to refactor recommendations."],
            "ranked_candidates": []
        }

    # Deduplicate by underlying model family so variants (e.g. 3.8 Med vs 3.8 Low)
    # do not displace genuine alternatives from other architectures and providers.
    family_representatives = []
    seen_families = set()
    family_modes = {}

    for r in rows:
        fam = _canonical_family(r["model_id"], r["display_name"])
        effort = (r.get("reasoning_effort") or "").capitalize()
        if fam not in family_modes:
            family_modes[fam] = []
        if effort and effort not in family_modes[fam]:
            family_modes[fam].append(effort)

        if fam not in seen_families:
            seen_families.add(fam)
            r["family_key"] = fam
            family_representatives.append(r)

    # Attach variant info to each family champion
    for rep in family_representatives:
        fam = rep["family_key"]
        cur_effort = (rep.get("reasoning_effort") or "").capitalize()
        rep["all_modes"] = family_modes.get(fam, [])
        rep["other_modes"] = [m for m in family_modes.get(fam, []) if m != cur_effort]

    top_choice = family_representatives[0]

    # Select runner-up: prioritize a distinct family from an independent quota pool/provider
    runner_up = None
    for candidate in family_representatives[1:]:
        if candidate.get("pool_id") != top_choice.get("pool_id") or candidate.get("provider") != top_choice.get("provider"):
            runner_up = candidate
            break

    # If all available candidates share the same pool/provider, fall back to the next best distinct family
    if not runner_up and len(family_representatives) > 1:
        runner_up = family_representatives[1]

    # Dynamic Rationale tailored to active models and independent routing
    rationale = []
    top_name = top_choice["display_name"]
    top_id = top_choice["model_id"]
    harness = top_choice["harness"]

    if strategy == "quota_first":
        rationale.append(f"Top Quota Yield: {top_name} via {harness} delivers {top_choice['tasks_per_pool_cycle']} tasks per reset window (${top_choice['cost_per_completed_task']}/task).")
        if "flash" in top_id and tier_id >= 3:
            rationale.append("Caution: Flash models on Tier 3+ may experience retry loops and token inflation (~104k tokens/done).")
    else:
        rationale.append(f"Top Latency & Reliability: {top_name} via {harness} requires only {top_choice['success_adjusted_seconds']}s and {top_choice['success_adjusted_tokens']:,} tokens per completed task.")

    if runner_up:
        pool_diff = runner_up.get("pool_id") != top_choice.get("pool_id")
        pool_note = f" (independent quota pool: {runner_up['sub_name'] or runner_up['harness']})" if pool_diff else ""
        if strategy == "quota_first":
            rationale.append(f"Independent Alternate: {runner_up['display_name']} via {runner_up['harness']}{pool_note} delivers {runner_up['tasks_per_pool_cycle']} tasks per reset.")
        else:
            rationale.append(f"Independent Alternate: {runner_up['display_name']} via {runner_up['harness']}{pool_note} offers strong fallback at {runner_up['success_adjusted_seconds']}s per completed task.")

    return {
        "tier_id": tier_id,
        "strategy": strategy,
        "top_recommendation": top_choice,
        "runner_up": runner_up,
        "rationale": rationale,
        "ranked_candidates": family_representatives[:10]
    }

if __name__ == "__main__":
    rec = recommend(tier_id=2, strategy="quota_first")
    print("Top:", rec["top_recommendation"]["display_name"] if rec["top_recommendation"] else "None")
    print("Runner up:", rec["runner_up"]["display_name"] if rec["runner_up"] else "None")
