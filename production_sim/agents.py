import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage as LCHumanMessage, AIMessage as LCAIMessage
from production_sim.helper import create_ai_message, calculate_score, score_breakdown_md

# Rules placed FIRST so the small model sees them before context.
# Written to guide WITHOUT killing the ability to engage with the student's question.
_LEVEL_RULES = {
    1: (
        "⛔ STRICT MODE (Level 1): NEVER write code, pseudocode, or implementations.\n"
        "✅ Ask 1-2 short guiding questions that help the student think for themselves.\n"
        "✅ Keep it to 1-3 sentences. Guide, don't explain. No code whatsoever.\n\n"
        "EXAMPLE — student asks about a class method:\n"
        "  BAD: 'You should override area() and return M_PI*r*r' (too much)\n"
        "  BAD: 'double area() override { return M_PI*r*r; }' (code — forbidden)\n"
        "  GOOD: 'What does a pure virtual method mean for subclasses? What formula gives the area?'"
    ),
    2: (
        "⛔ GUIDED MODE (Level 2): NEVER write code or pseudocode.\n"
        "✅ Give a short conceptual explanation (2-4 sentences) in plain words.\n"
        "✅ Point the student in the right direction without giving the solution.\n\n"
        "EXAMPLE — student asks about a class method:\n"
        "  BAD: 'double area() override { return M_PI*r*r; }' (code — forbidden)\n"
        "  GOOD: 'Since area() is pure virtual in the base class, your subclass must override it. "
        "The method should compute and return the correct value using the stored field.'\n\n"
        "Use words only. No code snippets."
    ),
    3: (
        "SUPPORTED MODE (Level 3): You may give full explanations with code examples.\n"
        "Be thorough, clear, and educational."
    ),
}

_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_C_CODE_RE = re.compile(
    r"```|"
    r"\b(void|int|char|float|struct|for|while|if)\s*[\w(].*\{|"
    r"\*\w+\s*=\s*\*\w+",
    re.DOTALL,
)


def _has_code(text: str) -> bool:
    return bool(_C_CODE_RE.search(text))


def _build_history(messages, max_turns: int = 6):
    """Convert graph messages to LangChain message objects for LLM context."""
    lc_msgs = []
    for m in messages:
        name = type(m).__name__
        if name == "HumanMessage":
            lc_msgs.append(LCHumanMessage(content=m.content))
        elif name == "AIMessage":
            lc_msgs.append(LCAIMessage(content=m.content))
    return lc_msgs[-max_turns:]


class AgentNodes:
    def __init__(self, model_name="openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            model=model_name,
            temperature=0.3,
            timeout=120,
            # Bound worst-case response length so a single reply can't run away.
            max_tokens=500,
        )

    def _chat(self, system_text: str, history: list, help_level: int) -> str:
        """Call LLM with conversation history; re-invoke once if code leaks at level < 3."""
        try:
            response = self.llm.invoke([SystemMessage(content=system_text)] + history)
            text = response.content
        except Exception as e:
            print(f"⚠️ LLM connection error: {e}")
            return "⚠️ Connection error — check your internet connection and GROQ_API_KEY, then try again."

        if help_level < 3 and _has_code(text):
            fallback = (
                f"{_LEVEL_RULES[help_level]}\n\n"
                "⚠️ Your previous response was rejected — it contained code.\n"
                "Rewrite: no code, 1-3 sentences only."
            )
            try:
                retry = self.llm.invoke([SystemMessage(content=fallback)] + history[-2:])
                text = retry.content
            except Exception:
                pass
            text = _CODE_FENCE_RE.sub("[code removed — help level 1/2]", text)

        return text

    # ── TUTOR NODE ─────────────────────────────────────────────────────────────
    def tutor_node(self, state):
        new_state = state.copy()
        scenario = state["scenario_data"]
        messages = list(state.get("messages", []))

        parts = scenario.get("parts", [])
        current_idx = state.get("current_part_index", -1)
        is_multipart = bool(parts) and current_idx >= 0

        # First turn: brief greeting only (task is shown in the UI expander)
        if not state.get("task_presented", False):
            greeting = "👋 Hello! I'm here to help. Ask me any questions about the task."
            new_state["messages"] = [create_ai_message(greeting)]
            new_state["task_presented"] = True
            new_state["help_level"] = 1
            return new_state

        # Every question starts at level 1; escalates only if the student says
        # they didn't understand the SAME question, resets on a new question.
        level = self.compute_question_level(state)
        state = {**state, "help_level": level}
        system_text, history = self._build_tutor_system(state)
        reply = self._chat(system_text, history, level)

        hpl = dict(state.get("hints_per_level", {1: 0, 2: 0, 3: 0}))
        hpl[level] = hpl.get(level, 0) + 1

        new_state["help_level"] = level
        new_state["hints_per_level"] = hpl
        new_state["hint_count"] = state.get("hint_count", 0) + 1
        new_state["messages"] = [create_ai_message(reply)]
        return new_state

    def _classify_continuation(self, prior_ai_text: str, latest_user_text: str) -> bool:
        """True if the student is saying they didn't understand / need more help
        on the SAME question the tutor just answered; False if this is a new
        or different question."""
        system = (
            "You classify one turn of a student/tutor chat in a programming course.\n\n"
            f"TUTOR'S LAST REPLY:\n{prior_ai_text}\n\n"
            f"STUDENT'S NEW MESSAGE:\n{latest_user_text}\n\n"
            "Classify the student's new message as SAME or NEW:\n\n"
            "SAME — the student is only expressing that they still don't understand "
            "or are still confused about the tutor's last reply itself (e.g. \"I "
            "don't get it\", \"can you explain again\", \"still confused\", \"what "
            "do you mean\"). It does not introduce any concept, term, or question "
            "beyond what the tutor's last reply already covered.\n\n"
            "NEW — the student asks about a different concept, function, or angle "
            "on the problem — anything not already explained in the tutor's last "
            "reply — even if it's on the same overall task. A specific, answerable "
            "question is NEW even when it's related to the same task; only a bare "
            "expression of confusion with no new content is SAME.\n\n"
            "When genuinely unsure, prefer NEW.\n\n"
            "Reply with exactly one word: SAME or NEW."
        )
        try:
            resp = self.llm.invoke([SystemMessage(content=system)])
            return resp.content.strip().upper().startswith("SAME")
        except Exception:
            return False

    def compute_question_level(self, state) -> int:
        """Per-question help level: every question starts at level 1. If the
        student's latest message indicates they didn't understand / need more
        help on the same question as the tutor's last reply, escalate one
        level (capped at 3). A new/different question resets to level 1."""
        if not state.get("task_presented", False) or state.get("hint_count", 0) == 0:
            return 1

        messages = list(state.get("messages", []))
        latest_user, prior_ai = None, None
        for m in reversed(messages):
            name = type(m).__name__
            if latest_user is None and name == "HumanMessage":
                latest_user = m.content
            elif latest_user is not None and name == "AIMessage":
                prior_ai = m.content
                break

        if not latest_user or not prior_ai:
            return 1

        current_level = state.get("help_level", 1)
        if self._classify_continuation(prior_ai, latest_user):
            return min(current_level + 1, 3)
        return 1

    def _build_tutor_system(self, state) -> tuple[str, list]:
        """Return (system_text, lc_history) for both streaming and non-streaming paths."""
        scenario = state["scenario_data"]
        help_level = state.get("help_level", 1)
        messages = list(state.get("messages", []))
        parts = scenario.get("parts", [])
        current_idx = state.get("current_part_index", -1)
        if bool(parts) and current_idx >= 0:
            part = parts[current_idx]
            task_context = (
                f"CURRENT TASK ({current_idx + 1}/{len(parts)}): {part['title']}\n"
                f"{part['description']}\n\n"
                f"SCENARIO: {scenario['name']}"
            )
        else:
            task_context = f"TASK:\n{scenario['dev_requirement']}"
        system_text = (
            "You are a C/C++ programming tutor at a university.\n"
            f"The student is currently working on:\n{task_context}\n\n"
            "LANGUAGE RULE: Always respond in English only, regardless of what language the student writes in.\n\n"
            "────────────────────────────────\n"
            f"{_LEVEL_RULES[help_level]}\n"
            "────────────────────────────────\n"
            "Answer the student's latest question. Stay focused on their actual task above. "
            "Do NOT grade or evaluate code."
        )
        return system_text, _build_history(messages)

    def stream_tutor_response(self, state):
        """Yield tokens for Streamlit st.write_stream().
        Level 3: true token streaming.
        Levels 1/2: full invoke first (so code detection works), then yield result.
        """
        help_level = state.get("help_level", 1)
        system_text, history = self._build_tutor_system(state)

        if help_level == 3:
            try:
                for chunk in self.llm.stream([SystemMessage(content=system_text)] + history):
                    if chunk.content:
                        yield chunk.content
            except Exception as e:
                yield f"\n\n⚠️ Connection error — check your internet connection and GROQ_API_KEY. ({e})"
        else:
            # Enforce no-code rule before showing anything
            reply = self._chat(system_text, history, help_level)
            yield reply

    # ── EVALUATOR NODE ─────────────────────────────────────────────────────────
    def evaluator_node(self, state):
        new_state = state.copy()
        scenario = state["scenario_data"]
        submitted_code = state.get("submitted_code", "")
        help_level = state.get("help_level", 2)
        hint_count = state.get("hint_count", 0)

        system_text = (
            "You are a strict C/C++ code evaluator for a university course.\n\n"
            f"REQUIREMENTS CHECKLIST:\n{scenario['requirements']}\n\n"
            f"SUCCESS CRITERIA:\n{scenario['validation_criteria']}\n\n"
            "Evaluate the submitted code ONLY against the checklist and criteria above.\n"
            "Check for memory management, pointer correctness, and edge cases.\n\n"
            "Respond in this exact format:\n"
            "RESULT: PASS or FAIL\n"
            "FEEDBACK: One short paragraph — what was done correctly and what (if anything) is missing."
        )

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_text),
                LCHumanMessage(content=f"CODE TO EVALUATE:\n{submitted_code}"),
            ])
            passed = "PASS" in response.content.upper() and "FAIL" not in response.content.upper().split("PASS")[0]
            feedback = response.content
        except Exception as e:
            print(f"⚠️ Evaluator error: {e}")
            passed = False
            feedback = "Could not evaluate the submission. Please try again."

        hints_per_level = state.get("hints_per_level", {1: 0, 2: 0, 3: 0})
        failed_runs = state.get("failed_runs", 0)
        score = calculate_score(hints_per_level, failed_runs, passed)
        breakdown = score_breakdown_md(hints_per_level, failed_runs, passed)

        result_icon = "✅ PASS" if passed else "❌ FAIL"
        summary = f"{result_icon}\n\n{feedback}\n\n{breakdown}"

        new_state["score"] = score
        new_state["current_phase"] = "done"
        new_state["messages"] = [create_ai_message(summary)]
        return new_state
