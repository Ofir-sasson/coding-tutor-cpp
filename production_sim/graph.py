from langgraph.graph import StateGraph, END
from .state import TutorState
from .agents import AgentNodes
from .scenarios import ScenarioManager


class CodingTutorSim:
    def __init__(self, student_id: str, help_level: int = 1, completed_scenarios: list = None):
        self.student_id = student_id
        self.help_level = help_level
        self.completed_scenarios = completed_scenarios or []
        self.nodes = AgentNodes(model_name="qwen2.5-coder:7b")
        self.scenario_manager = ScenarioManager()
        self.workflow = StateGraph(TutorState)
        self._build_graph()

    def _build_graph(self):
        self.workflow.add_node("router", self._router_node)
        self.workflow.add_node("tutor", self.nodes.tutor_node)
        self.workflow.add_node("evaluator", self.nodes.evaluator_node)

        self.workflow.set_entry_point("router")

        self.workflow.add_conditional_edges(
            "router",
            self._route,
            {
                "chat": "tutor",
                "evaluation": "evaluator",
            },
        )

        self.workflow.add_edge("tutor", END)
        self.workflow.add_edge("evaluator", END)

    def _router_node(self, state):
        return {}

    def _route(self, state):
        return state.get("current_phase", "chat")

    def compile(self):
        return self.workflow.compile()

    def get_initial_state(self):
        scenario = self.scenario_manager.get_scenario(
            student_id=self.student_id,
            exclude_ids=self.completed_scenarios,
        )
        has_parts = bool(scenario.get("parts"))
        return {
            "messages": [],
            "current_phase": "chat",
            "help_level": self.help_level,
            "scenario_id": scenario["id"],
            "scenario_data": scenario,
            "hint_count": 0,
            "hints_per_level": {1: 0, 2: 0, 3: 0},
            "failed_runs": 0,
            "submitted_code": "",
            "score": 0,
            "student_id": self.student_id,
            "task_presented": False,
            "current_part_index": 0 if has_parts else -1,
            "parts_results": [],
        }
