#!/usr/bin/env python3
"""
Dynamic Task Complexity Classifier & Auto-Router for OmniBurn.
Inspired by RouteLLM and Not Diamond predictive routing heuristics.
Inspects real-time git status, diff footprint, modified file scope, and prompt intent
to classify coding tasks into Workload Tiers 1-4 with zero external API latency.
"""

import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

TIER_METADATA = {
    1: {
        "name": "Tier 1: Micro-Task / Syntax / Quick Fix",
        "description": "Quick fixes, syntax correction, docstrings, formatting, and low-risk single-file edits.",
        "typical_tokens": 1000,
        "default_strategy": "quota_first",
    },
    2: {
        "name": "Tier 2: Standard Engineering",
        "description": "Routine engineering: unit tests, single-feature implementations, bug fixes, and targeted refactors.",
        "typical_tokens": 10000,
        "default_strategy": "quota_first",
    },
    3: {
        "name": "Tier 3: Long-Horizon Multi-File Feature",
        "description": "Complex engineering spanning multiple files, service contracts, integration bugs, and deep debugging.",
        "typical_tokens": 50000,
        "default_strategy": "time_reliability_first",
    },
    4: {
        "name": "Tier 4: Heavy Agentic / Repo-Scale Architecture",
        "description": "Whole-repository architectural refactors, schema migrations, massive context synthesis, and autonomous multi-turn loops.",
        "typical_tokens": 200000,
        "default_strategy": "time_reliability_first",
    },
}

INTENT_KEYWORDS = {
    1: [
        "typo", "syntax", "lint", "format", "docstring", "comment", "rename",
        "one-liner", "quick fix", "simple fix", "explain this function", "minor tweak",
        "cleanup import", "type annotation", "readme", "spelling", "css", "styling", "color"
    ],
    2: [
        "unit test", "write tests", "test case", "implement function", "single feature",
        "bugfix", "debug error", "stack trace", "fix exception", "add endpoint",
        "helper method", "validate input", "controller", "endpoint", "api", "component",
        "script", "handler", "logic", "tests"
    ],
    3: [
        "multi-file", "refactor", "service layer", "database migration", "integration",
        "contract", "api breaking change", "wire up", "pipeline", "state management",
        "performance optimization", "race condition", "cross-module", "database", "schema",
        "auth", "authentication", "middleware", "jwt", "oauth", "cache", "redis", "docker"
    ],
    4: [
        "architecture", "rearchitect", "repo-scale", "monorepo", "whole codebase",
        "system redesign", "end-to-end rewrite", "autonomous loop", "massive context",
        "multi-agent", "framework migration", "deep reasoning", "core abstractions",
        "microservices", "entire repository", "full stack rewrite", "build an app"
    ],
}


def _run_git_cmd(cmd: List[str], cwd: Optional[str] = None) -> Optional[str]:
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd or os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout
    except Exception:
        pass
    return None


def get_git_workspace_stats(repo_path: Optional[str] = None) -> Dict[str, Any]:
    cwd = repo_path or os.getcwd()
    status_out = _run_git_cmd(["git", "status", "--porcelain"], cwd=cwd)
    if status_out is None:
        return {
            "is_git_repo": False,
            "modified_files": [],
            "file_count": 0,
            "additions": 0,
            "deletions": 0,
            "diff_chars": 0,
        }

    modified_files = []
    for line in status_out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            modified_files.append(parts[1])

    diff_out = _run_git_cmd(["git", "diff", "HEAD"], cwd=cwd) or ""
    if not diff_out and modified_files:
        diff_out = _run_git_cmd(["git", "diff"], cwd=cwd) or ""

    additions = 0
    deletions = 0
    for diff_line in diff_out.splitlines():
        if diff_line.startswith("+") and not diff_line.startswith("+++"):
            additions += 1
        elif diff_line.startswith("-") and not diff_line.startswith("---"):
            deletions += 1

    return {
        "is_git_repo": True,
        "modified_files": modified_files,
        "file_count": len(modified_files),
        "additions": additions,
        "deletions": deletions,
        "diff_chars": len(diff_out),
    }


def classify_workload(
    prompt: Optional[str] = None,
    repo_path: Optional[str] = None,
    diff_text: Optional[str] = None,
    preferred_strategy: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Classifies a task into Workload Tier 1, 2, 3, or 4 with rationale signals.
    """
    prompt_str = (prompt or "").strip()
    prompt_lower = prompt_str.lower()
    signals: List[str] = []

    # 1. Analyze Git Workspace
    inspect_git = (repo_path is not None) or (diff_text is not None) or (not prompt_str)
    if inspect_git:
        workspace = get_git_workspace_stats(repo_path)
    else:
        workspace = {"is_git_repo": False, "modified_files": [], "file_count": 0, "additions": 0, "deletions": 0, "diff_chars": 0}

    if diff_text:
        workspace["diff_chars"] = len(diff_text)
        workspace["additions"] = sum(1 for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
        workspace["deletions"] = sum(1 for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---"))

    file_count = workspace["file_count"]
    total_diff_lines = workspace["additions"] + workspace["deletions"]

    # 2. Keyword & Intent Scoring
    tier_intent_scores = {1: 0, 2: 0, 3: 0, 4: 0}
    matched_keywords = {1: [], 2: [], 3: [], 4: []}

    for tier, kw_list in INTENT_KEYWORDS.items():
        for kw in kw_list:
            if re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower):
                tier_intent_scores[tier] += 2
                matched_keywords[tier].append(kw)

    # 3. Workspace Scope Scoring
    if file_count == 0:
        pass
    elif file_count == 1:
        tier_intent_scores[1] += 1
        tier_intent_scores[2] += 2
        signals.append("Single modified file detected in workspace")
    elif 2 <= file_count <= 4:
        tier_intent_scores[2] += 2
        tier_intent_scores[3] += 3
        signals.append(f"Multi-file scope: {file_count} files modified across workspace")
    elif 5 <= file_count <= 9:
        tier_intent_scores[3] += 4
        tier_intent_scores[4] += 2
        signals.append(f"Substantial workspace scope: {file_count} files modified")
    else:
        tier_intent_scores[4] += 5
        signals.append(f"Repo-scale workspace footprint: {file_count} files modified")

    if total_diff_lines > 0:
        if total_diff_lines < 30:
            tier_intent_scores[1] += 2
            tier_intent_scores[2] += 1
            signals.append(f"Small diff volume: {total_diff_lines} lines (+{workspace['additions']}/-{workspace['deletions']})")
        elif total_diff_lines < 200:
            tier_intent_scores[2] += 3
            signals.append(f"Moderate diff volume: {total_diff_lines} lines (+{workspace['additions']}/-{workspace['deletions']})")
        elif total_diff_lines < 600:
            tier_intent_scores[3] += 4
            signals.append(f"Large diff volume: {total_diff_lines} lines (+{workspace['additions']}/-{workspace['deletions']})")
        else:
            tier_intent_scores[4] += 5
            signals.append(f"Massive diff volume: {total_diff_lines} lines (+{workspace['additions']}/-{workspace['deletions']})")

    # 4. Resolve Predicted Tier
    if matched_keywords[4]:
        tier_intent_scores[4] += 5
        signals.append(f"Detected architectural keywords: {', '.join(matched_keywords[4])}")
    if matched_keywords[3]:
        tier_intent_scores[3] += 4
        signals.append(f"Detected multi-file keywords: {', '.join(matched_keywords[3])}")
    if matched_keywords[2]:
        tier_intent_scores[2] += 3
        signals.append(f"Detected engineering keywords: {', '.join(matched_keywords[2])}")
    if matched_keywords[1]:
        tier_intent_scores[1] += 5
        signals.append(f"Detected micro-task keywords: {', '.join(matched_keywords[1])}")

    # Fallback to Tier 2 if no strong signals
    if not prompt_str and file_count == 0:
        predicted_tier = 2
        confidence = 0.60
        signals.append("Clean workspace with no prompt provided; defaulting to Tier 2 standard engineering")
    else:
        # Sort tiers by score descending
        sorted_tiers = sorted(tier_intent_scores.items(), key=lambda x: (x[1], x[0]), reverse=True)
        top_tier, top_score = sorted_tiers[0]
        if top_score == 0:
            predicted_tier = 2
            confidence = 0.65
            signals.append("General task intent without strong polarity; mapped to Tier 2")
        else:
            predicted_tier = top_tier
            second_score = sorted_tiers[1][1] if len(sorted_tiers) > 1 else 0
            spread = max(1, top_score - second_score)
            confidence = min(0.96, 0.68 + (spread * 0.05))

    meta = TIER_METADATA[predicted_tier]
    strategy = preferred_strategy or meta["default_strategy"]

    # Estimated Token Volume
    base_tokens = meta["typical_tokens"]
    if workspace["diff_chars"] > 0:
        diff_tokens = int(workspace["diff_chars"] / 3.6)
        estimated_tokens = max(base_tokens, min(180000, base_tokens + diff_tokens))
    else:
        estimated_tokens = base_tokens

    intent_label = {
        1: "micro_syntax",
        2: "standard_engineering",
        3: "multi_file_feature",
        4: "repo_scale_architecture",
    }[predicted_tier]

    return {
        "tier_id": predicted_tier,
        "tier_label": meta["name"],
        "tier_description": meta["description"],
        "confidence": round(confidence, 2),
        "estimated_tokens": estimated_tokens,
        "intent": intent_label,
        "recommended_strategy": strategy,
        "signals": signals,
        "workspace_stats": workspace,
        "prompt_summary": (prompt_str[:120] + "...") if len(prompt_str) > 120 else prompt_str,
        "has_explicit_input": bool(prompt_str or file_count > 0),
    }


if __name__ == "__main__":
    import json
    res = classify_workload("refactor the database layer to support postgres pool connection across all engines")
    print(json.dumps(res, indent=2))
