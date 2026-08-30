from typing import TypedDict, List, Annotated, Literal
from langchain_core.messages import BaseMessage
from production_sim.helper import add_unique_messages


class TutorState(TypedDict):
    messages: Annotated[List[BaseMessage], add_unique_messages]
    current_phase: Literal["chat", "evaluation", "done"]
    help_level: int          # 1=Strict, 2=Guided, 3=Supported — per-question, auto-escalates
    scenario_id: str
    scenario_data: dict
    hint_count: int          # total chat questions asked (all levels)
    hints_per_level: dict    # {1: count, 2: count, 3: count} — for per-level penalty
    failed_runs: int         # number of times code failed to compile/pass tests
    submitted_code: str
    score: int
    student_id: str
    task_presented: bool
    current_part_index: int  # 0-based for multi-part scenarios; -1 for single-submission
    parts_results: list      # [{part_id, passed, feedback}] for multi-part
