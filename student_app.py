"""
Student Coding Tutor — C/C++
Run with: streamlit run student_app.py
"""

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from production_sim.auto_tester import auto_test, check_syntax
from production_sim.helper import calculate_score, score_breakdown_md
from app_shared import (
    LEVEL_LABELS, LEVEL_DESCRIPTIONS,
    update_session_current, complete_session, save_chat_log,
    run_graph, start_student_session, get_completed_scenarios,
    render_dark_mode_toggle,
)

IDE_CSS = """
<style>
div[data-testid="stTextArea"] textarea {
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}
</style>
"""

SINGLE_PLACEHOLDER = """\
#include <stdio.h>
#include <stdlib.h>

// Write your solution here

int main() {

    return 0;
}"""


def _code_editor_height(text, minimum=350, maximum=800, px_per_line=22, base_padding=40):
    """Grow the editor to fit its content (up to a cap, then it scrolls like before).
    Streamlit's text_area only re-renders on blur/Ctrl+Enter, not per keystroke,
    so the box grows a beat after typing rather than character-by-character —
    still much less scrolling than a fixed small box for longer answers."""
    lines = (text or "").count("\n") + 1
    return int(min(maximum, max(minimum, lines * px_per_line + base_padding)))


# ── Session state ─────────────────────────────────────────────────────────────

def init():
    defaults = {
        "started": False,
        "student_id": "",
        "graph_app": None,
        "agent_nodes": None,
        "graph_state": None,
        "chat_history": [],
        "log_saved": False,
        # multi-part tracking
        "current_part_index": 0,
        "frontier_part_index": 0,  # furthest part reached — caps how far "jump" navigation can go
        "parts_passed": [],
        "parts_code": [],   # accumulated code from each passed part (accumulate_code scenarios)
        "part_test_result": None,
        "single_syntax_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_part_state():
    st.session_state.current_part_index = 0
    st.session_state.frontier_part_index = 0
    st.session_state.parts_passed = []
    st.session_state.parts_code = []
    st.session_state.part_test_result = None


# ── ID Entry screen ───────────────────────────────────────────────────────────

def screen_id_entry():
    render_dark_mode_toggle()
    st.markdown(
        "<h1 style='text-align:center'>🎓 Coding Tutor – C/C++</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:gray'>"
        "סביבת בחינה מבוססת AI | המכללה האקדמית להנדסה ירושלים"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col = st.columns([1, 2, 1])[1]
    with col:
        student_id = st.text_input("הזן מספר תעודת זהות:", key="id_input")
        if st.button("התחל בחינה", type="primary", use_container_width=True):
            if student_id.strip():
                with st.spinner("טוען מטלה..."):
                    app, nodes, state, chat_msgs = start_student_session(student_id.strip())
                st.session_state.graph_app = app
                st.session_state.agent_nodes = nodes
                st.session_state.graph_state = state
                st.session_state.student_id = student_id.strip()
                st.session_state.chat_history = chat_msgs
                st.session_state.started = True
                st.session_state.log_saved = False
                _reset_part_state()
                st.rerun()
            else:
                st.warning("נא להזין מספר תעודת זהות.")


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(gs, is_done):
    render_dark_mode_toggle()
    with st.sidebar:
        st.markdown(f"**סטודנט:** `{st.session_state.student_id}`")

        if gs:
            current_level = gs.get("help_level", 1)
            st.markdown(f"**רמת עזרה נוכחית:** {current_level} – {LEVEL_LABELS.get(current_level, '?')}")
            st.caption(
                "כל שאלה חדשה מתחילה ברמה 1. אם תגידו שלא הבנתם או תבקשו עוד עזרה, "
                "הרמה תעלה אוטומטית עבור אותה שאלה בלבד."
            )
            completed_count = len(get_completed_scenarios(st.session_state.student_id))
            if completed_count:
                st.markdown(f"**שאלות שהושלמו:** {completed_count}")
            st.markdown(f"**רמזים:** {gs.get('hint_count', 0)}")
            phase_map = {"chat": "💬 שיחה", "evaluation": "🔍 הערכה", "done": "🏁 הסתיים"}
            st.markdown(f"**שלב:** {phase_map.get(gs.get('current_phase', 'chat'), '')}")
            if is_done:
                st.markdown(f"**ציון:** {gs.get('score', 0)}/100")

        st.markdown("---")
        if st.button("🚪 סיום וסגירה", use_container_width=True):
            for k in ["started", "graph_state", "graph_app", "student_id", "log_saved"]:
                st.session_state[k] = False if isinstance(st.session_state.get(k), bool) else None
            st.session_state.chat_history = []
            _reset_part_state()
            st.rerun()


# ── Chat column (shared) ──────────────────────────────────────────────────────

def render_chat_column(gs):
    st.markdown("#### 💬 שאל את המורה")
    with st.container(height=370):
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    with st.form("chat_form", clear_on_submit=True, border=False):
        c_inp, c_btn = st.columns([5, 1])
        with c_inp:
            prompt = st.text_input(
                "", placeholder="שאל שאלה על המטלה...",
                label_visibility="collapsed",
            )
        with c_btn:
            send = st.form_submit_button("שלח", use_container_width=True)

    if send and prompt.strip():
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        # Build full conversation history from chat_history (source of truth)
        lc_msgs = []
        for m in st.session_state.chat_history[-8:]:
            if m["role"] == "user":
                lc_msgs.append(HumanMessage(content=m["content"]))
            else:
                lc_msgs.append(AIMessage(content=m["content"]))
        gs["messages"] = lc_msgs

        nodes = st.session_state.get("agent_nodes")
        if nodes:
            # Every question starts at level 1; escalates only if the student
            # indicates they didn't understand the SAME question (using the
            # full chat history for context), resets on a new question.
            prev_level = gs.get("help_level", 1)
            level = nodes.compute_question_level(gs)
            gs["help_level"] = level
            if level > prev_level:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": (
                        f"ℹ️ **עולה לרמה {level} – {LEVEL_LABELS[level]} עבור השאלה הזו.**  \n"
                        f"{LEVEL_DESCRIPTIONS[level]}"
                    ),
                })

            with st.chat_message("assistant"):
                if level == 3:
                    # True token-by-token streaming.
                    response_text = st.write_stream(nodes.stream_tutor_response(gs))
                else:
                    # Levels 1/2 compute the full reply before yielding (needed
                    # to filter out leaked code), so write_stream would leave the
                    # bubble blank the whole time — looked like the chat froze.
                    # Show a spinner instead so it's clear it's working.
                    with st.spinner("💭 חושב על תשובה..."):
                        response_text = "".join(nodes.stream_tutor_response(gs))
                    st.markdown(response_text)
            gs["hint_count"] = gs.get("hint_count", 0) + 1
            # Track per-level hint count for granular scoring
            hpl = gs.get("hints_per_level", {1: 0, 2: 0, 3: 0})
            hpl[level] = hpl.get(level, 0) + 1
            gs["hints_per_level"] = hpl
            gs["task_presented"] = True
            st.session_state.graph_state = gs
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
            update_session_current(
                st.session_state.student_id,
                {"hint_count": gs.get("hint_count", 0)},
            )
        else:
            with st.spinner("חושב..."):
                new_state, new_msgs = run_graph(st.session_state.graph_app, gs)
            st.session_state.graph_state = new_state
            update_session_current(
                st.session_state.student_id,
                {"hint_count": new_state.get("hint_count", 0)},
            )
            for msg in new_msgs:
                st.session_state.chat_history.append({"role": "assistant", "content": msg.content})
        st.rerun()


# ── Multi-part exam screen ───────────────────────────────────────────────────

def _finish_multipart(gs, scenario, parts):
    """Called when all parts are passed. Save log, complete session, show result."""
    hints_per_level = gs.get("hints_per_level", {1: 0, 2: 0, 3: 0})
    failed_runs = gs.get("failed_runs", 0)
    hint_count = gs.get("hint_count", 0)
    score = calculate_score(hints_per_level, failed_runs, passed=True)

    if not st.session_state.log_saved:
        save_chat_log(
            st.session_state.student_id, scenario["name"],
            hints_per_level, st.session_state.chat_history,
            score, hint_count,
        )
        complete_session(st.session_state.student_id, score, hint_count)
        st.session_state.log_saved = True
        gs["score"] = score
        gs["current_phase"] = "done"
        st.session_state.graph_state = gs

    st.success(f"🏆 כל החלקים עברו! ציון סופי: **{score}/100**")
    st.markdown(score_breakdown_md(hints_per_level, failed_runs, passed=True))
    st.info("ניתן לסגור את החלון או ללחוץ 'סיום וסגירה'.")
    st.markdown("### שיחת הצ'אט")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    st.stop()


def _first_unpassed_index(parts, parts_passed, start=0):
    """Next part the student hasn't passed yet, searching forward from `start` (wraps around)."""
    n = len(parts)
    for offset in range(n):
        i = (start + offset) % n
        if parts[i]["part_id"] not in parts_passed:
            return i
    return start


def screen_exam_multipart(gs, scenario, parts):
    parts_passed = st.session_state.parts_passed
    num_parts = len(parts)
    use_accumulation = scenario.get("accumulate_code", False)
    carry_forward = scenario.get("carry_forward_code", False)
    # Both flags mean parts depend on order (a later part needs code from an
    # earlier one — either concatenated in, or pre-filled into its editor),
    # so navigation may only go back to parts already reached, not skip ahead.
    depends_on_order = use_accumulation or carry_forward

    # All done?
    if len(parts_passed) >= num_parts:
        _finish_multipart(gs, scenario, parts)
        return

    current_idx = st.session_state.current_part_index
    # Guard against index out of range
    if current_idx >= num_parts:
        current_idx = num_parts - 1
        st.session_state.current_part_index = current_idx

    frontier = st.session_state.get("frontier_part_index", 0)
    if frontier >= num_parts:
        frontier = num_parts - 1
    frontier = max(frontier, current_idx)
    st.session_state.frontier_part_index = frontier

    current_part = parts[current_idx]

    # ── Progress bar (clickable — jump between parts) ──
    # Independent scenarios allow answering the parts in any order. Scenarios
    # where parts depend on earlier ones can only jump within [0, frontier] —
    # i.e. review anything already reached, but not skip ahead unattempted.
    st.markdown(f"### 📋 {scenario['name']}")
    prog_cols = st.columns(num_parts)
    for i, p in enumerate(parts):
        with prog_cols[i]:
            pid = p["part_id"]
            is_passed = pid in parts_passed
            is_current = i == current_idx
            label = f"✅ {p['title']}" if is_passed else (f"🔵 {p['title']}" if is_current else f"⬜ {p['title']}")
            can_jump = (not depends_on_order or i <= frontier) and not is_current
            if is_current:
                st.info(f"**{label}**")
            elif can_jump:
                if st.button(label, key=f"jump_part_{i}", use_container_width=True):
                    st.session_state.current_part_index = i
                    st.session_state.part_test_result = None
                    st.rerun()
            else:
                st.markdown(
                    f"<div style='text-align:center;color:gray;padding:8px'>{label}</div>",
                    unsafe_allow_html=True,
                )
    st.markdown("---")

    # ── Review history: last code typed for each part already passed ──
    reviewable = [
        (i, p) for i, p in enumerate(parts)
        if p["part_id"] in parts_passed and st.session_state.get(f"code_part_{i}", "").strip()
    ]
    if reviewable:
        with st.expander("📜 היסטוריית חלקים שהושלמו"):
            for i, p in reviewable:
                st.markdown(f"**{p['title']}**")
                st.code(
                    st.session_state.get(f"code_part_{i}", ""),
                    language="cpp" if p.get("language") == "cpp" else "c",
                )

    # ── Part header ──
    st.markdown(f"#### חלק {current_idx + 1}/{num_parts}: `{current_part['title']}`")
    with st.expander("📄 תיאור המשימה", expanded=True):
        st.markdown(current_part["description"])

    # ── Two-column layout ──
    col_code, col_chat = st.columns([1, 1], gap="medium")

    with col_code:
        st.markdown("#### ✏️ עורך קוד")
        placeholder_text = (
            f"// Implement: {current_part['title']}\n"
            "// Do NOT write main() — the system tests automatically.\n\n"
        )
        _part_code_key = f"code_part_{current_idx}"
        code = st.text_area(
            label="",
            height=_code_editor_height(st.session_state.get(_part_code_key, "")),
            key=_part_code_key,
            placeholder=placeholder_text,
            label_visibility="collapsed",
        )

        # Show last test result
        result = st.session_state.part_test_result
        if result:
            if result["passed"]:
                st.success(result["feedback"])
            else:
                st.error(result["feedback"])

        col_syntax, col_run = st.columns(2)
        with col_syntax:
            syntax_clicked = st.button("🔎 בדוק תחביר בלבד", use_container_width=True)
        with col_run:
            run_clicked = st.button("▶️ בדוק קוד", type="primary", use_container_width=True)

        if syntax_clicked:
            if code.strip():
                with st.spinner("בודק תחביר..."):
                    syn_passed, syn_feedback = check_syntax(
                        code, current_part.get("language", "c"), current_part.get("setup", "")
                    )
                st.session_state.part_test_result = {"passed": syn_passed, "feedback": syn_feedback}
                st.rerun()
            else:
                st.warning("הקוד ריק!")

        if run_clicked:
            if code.strip():
                # Some scenarios are designed so each part builds on the functions
                # written in previous parts (e.g. my_strcpy calls my_strlen).
                # Only accumulate when the scenario declares accumulate_code=True.
                # For other scenarios the setup already provides reference
                # implementations, so prepending student code would cause
                # duplicate-definition errors.
                if use_accumulation and st.session_state.parts_code:
                    prev_code = "\n\n".join(st.session_state.parts_code)
                    full_student_code = prev_code + "\n\n" + code
                else:
                    full_student_code = code
                with st.spinner("מקמפל ומריץ בדיקות..."):
                    passed, feedback = auto_test(full_student_code, current_part)
                st.session_state.part_test_result = {"passed": passed, "feedback": feedback}

                if not passed:
                    gs["failed_runs"] = gs.get("failed_runs", 0) + 1
                    st.session_state.graph_state = gs

                if passed:
                    pid = current_part["part_id"]
                    if pid not in parts_passed:
                        parts_passed.append(pid)
                    st.session_state.parts_passed = parts_passed
                    if use_accumulation:
                        st.session_state.parts_code.append(code.strip())

                    # Update graph state for tutor awareness.
                    # Next part = first one not yet passed, searching forward from
                    # here — lets students who answered out of order (non-accumulate
                    # scenarios) land on whatever's still open, not just idx+1.
                    next_idx = _first_unpassed_index(parts, parts_passed, current_idx + 1)
                    gs["current_part_index"] = next_idx
                    gs["parts_results"] = gs.get("parts_results", []) + [
                        {"part_id": pid, "passed": True, "feedback": feedback}
                    ]
                    st.session_state.graph_state = gs
                    st.session_state.current_part_index = next_idx
                    st.session_state.frontier_part_index = max(
                        st.session_state.get("frontier_part_index", 0), next_idx
                    )
                    st.session_state.part_test_result = None

                    if carry_forward and next_idx != current_idx:
                        # Pre-fill the next part's editor with the code that just
                        # passed, so the student extends one growing definition
                        # in place instead of retyping it. Don't clobber a draft
                        # if they'd already visited that part before.
                        next_key = f"code_part_{next_idx}"
                        if not st.session_state.get(next_key, "").strip():
                            st.session_state[next_key] = code.strip()

                    if len(parts_passed) >= num_parts:
                        # All parts done
                        pass  # will be caught at top of next render
                    else:
                        next_part = parts[next_idx]
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": (
                                f"✅ **חלק {current_idx + 1} עבר!** (`{current_part['title']}`)\n\n"
                                f"עכשיו עובדים על חלק {next_idx + 1}: **`{next_part['title']}`** — ראה את תיאור המשימה למעלה. שאל אותי אם צריך עזרה!"
                            ),
                        })
                        update_session_current(
                            st.session_state.student_id,
                            {"hint_count": gs.get("hint_count", 0)},
                        )
                st.rerun()
            else:
                st.warning("הקוד ריק!")

    with col_chat:
        render_chat_column(gs)


# ── Single-submission exam screen ─────────────────────────────────────────────

def screen_exam_single(gs, scenario):
    is_done = gs and gs.get("current_phase") == "done"

    if is_done:
        if not st.session_state.log_saved:
            scenario_name = gs.get("scenario_data", {}).get("name", "unknown")
            save_chat_log(
                st.session_state.student_id, scenario_name,
                gs.get("hints_per_level", {1: 0, 2: 0, 3: 0}), st.session_state.chat_history,
                gs.get("score", 0), gs.get("hint_count", 0),
            )
            complete_session(
                st.session_state.student_id,
                gs.get("score", 0), gs.get("hint_count", 0),
            )
            st.session_state.log_saved = True

        st.success(f"🏆 הגשה הושלמה! ציון: {gs.get('score', 0)}/100")
        st.info("ניתן לסגור את החלון או ללחוץ 'סיום וסגירה' בסרגל הצד.")
        st.markdown("### שיחת הצ'אט")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        st.stop()

    st.markdown(f"### 📋 {scenario.get('name', '')}")
    with st.expander("📄 תיאור המשימה", expanded=True):
        st.markdown(scenario.get("dev_requirement", ""))

    col_code, col_chat = st.columns([1, 1], gap="medium")

    with col_code:
        st.markdown("#### ✏️ עורך קוד")
        code = st.text_area(
            label="",
            height=_code_editor_height(st.session_state.get("live_code", ""), minimum=430),
            key="live_code",
            placeholder=SINGLE_PLACEHOLDER,
            label_visibility="collapsed",
        )

        syn_result = st.session_state.single_syntax_result
        if syn_result:
            if syn_result["passed"]:
                st.success(syn_result["feedback"])
            else:
                st.error(syn_result["feedback"])

        col_syntax, col_submit = st.columns(2)
        with col_syntax:
            syntax_clicked = st.button("🔎 בדוק תחביר", use_container_width=True)
        with col_submit:
            submit_clicked = st.button("✅ הגש קוד", type="primary", use_container_width=True)

        if syntax_clicked:
            if code.strip():
                with st.spinner("בודק תחביר..."):
                    syn_passed, syn_feedback = check_syntax(code, "c")
                st.session_state.single_syntax_result = {"passed": syn_passed, "feedback": syn_feedback}
                st.rerun()
            else:
                st.warning("הקוד ריק!")

        if submit_clicked:
            if code.strip():
                st.session_state.chat_history.append(
                    {"role": "user", "content": f"```c\n{code}\n```"}
                )
                gs["submitted_code"] = code
                gs["current_phase"] = "evaluation"
                gs["messages"] = gs.get("messages", []) + [HumanMessage(content=code)]
                with st.spinner("מעריך את הקוד..."):
                    new_state, new_msgs = run_graph(st.session_state.graph_app, gs)
                st.session_state.graph_state = new_state
                for msg in new_msgs:
                    st.session_state.chat_history.append({"role": "assistant", "content": msg.content})
                st.rerun()
            else:
                st.warning("הקוד ריק!")

    with col_chat:
        render_chat_column(gs)


# ── Main exam screen (dispatcher) ─────────────────────────────────────────────

def screen_exam():
    gs = st.session_state.graph_state
    is_done = gs and gs.get("current_phase") == "done"
    render_sidebar(gs, is_done)

    st.markdown(IDE_CSS, unsafe_allow_html=True)
    st.title("🎓 Coding Tutor – C/C++")

    if not gs:
        st.error("שגיאה: אין מצב גרף. נסה לרענן.")
        return

    scenario = gs.get("scenario_data", {})
    parts = scenario.get("parts", [])

    if parts:
        screen_exam_multipart(gs, scenario, parts)
    else:
        screen_exam_single(gs, scenario)


# ── Entry point ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Coding Tutor – C/C++",
    page_icon="🎓",
    layout="wide",
)

init()

if not st.session_state.started:
    screen_id_entry()
else:
    screen_exam()
