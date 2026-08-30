"""Scoring and message-bookkeeping helpers shared by the LangGraph nodes."""

import uuid
from typing import List
from langchain_core.messages import AIMessage, BaseMessage

# ── Scoring constants ─────────────────────────────────────────────────────────
HINT_PENALTY = {1: 0.5, 2: 1.0, 3: 1.5}   # points deducted per question per level
FAILED_RUN_PENALTY = 1.0                    # points deducted per failed code run


def calculate_score(hints_per_level: dict, failed_runs: int, passed: bool = True) -> int:
    base = 100 if passed else 50
    hint_deduction = sum(hints_per_level.get(lvl, 0) * pen for lvl, pen in HINT_PENALTY.items())
    run_deduction = failed_runs * FAILED_RUN_PENALTY
    return max(0, round(base - hint_deduction - run_deduction))


def score_breakdown_md(hints_per_level: dict, failed_runs: int, passed: bool = True) -> str:
    base = 100 if passed else 50
    h1, h2, h3 = hints_per_level.get(1, 0), hints_per_level.get(2, 0), hints_per_level.get(3, 0)
    d_runs = failed_runs * FAILED_RUN_PENALTY
    d_h1, d_h2, d_h3 = h1 * 0.5, h2 * 1.0, h3 * 1.5
    total_ded = d_runs + d_h1 + d_h2 + d_h3
    final = max(0, round(base - total_ded))

    def _fmt(val: float) -> str:
        return f"−{val:.1f}" if val else "0"

    rows = [
        ("Base score", "—", "—", str(base)),
        ("Failed runs", str(failed_runs), "−1.0 each", _fmt(d_runs)),
        ("Hints – Level 1 (Strict)", str(h1), "−0.5 each", _fmt(d_h1)),
        ("Hints – Level 2 (Guided)", str(h2), "−1.0 each", _fmt(d_h2)),
        ("Hints – Level 3 (Supported)", str(h3), "−1.5 each", _fmt(d_h3)),
    ]
    table = "| Component | Count | Per unit | Deduction |\n|---|---|---|---|\n"
    for component, count, per, ded in rows:
        table += f"| {component} | {count} | {per} | {ded} |\n"
    table += f"| **Final Score** | | **Total −{total_ded:.1f}** | **{final}/100** |"
    return f"### 📊 Score Breakdown\n\n{table}"


def create_ai_message(content: str) -> AIMessage:
    """AIMessage with a unique id, so add_unique_messages can dedupe it."""
    return AIMessage(
        content=content,
        additional_kwargs={"id": str(uuid.uuid4())}
    )


def add_unique_messages(
    existing: List[BaseMessage],
    new: List[BaseMessage]
) -> List[BaseMessage]:
    """LangGraph reducer for TutorState.messages: append only messages whose
    id (set by create_ai_message) hasn't already been recorded, so a node
    that fires more than once in the same graph.stream() pass doesn't
    duplicate the same reply in the conversation."""
    seen_ids = {m.id for m in existing if getattr(m, "id", None)}

    unique_new = [
        m for m in new
        if getattr(m, "id", None) not in seen_ids
    ]

    return existing + unique_new
