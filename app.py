import os
import json
import streamlit as st
from datetime import datetime
from langchain_core.messages import HumanMessage
from production_sim import CodingTutorSim

CONFIG_FILE = "teacher_config.json"
SESSIONS_FILE = "sessions.json"
DEFAULT_PASSWORD = "teacher123"
LEVEL_LABELS = {1: "Strict", 2: "Guided", 3: "Supported"}
LEVEL_DESCRIPTIONS = {
    1: "שאלות מנחות בלבד – ללא תשובות ישירות",
    2: "רמזים קונספטואליים – ללא קוד",
    3: "הסבר מלא עם דוגמאות קוד",
}

CODE_PLACEHOLDER = """\
#include <stdio.h>
#include <stdlib.h>

// Write your solution here

int main() {

    return 0;
}"""

IDE_CSS = """
<style>
/* Monospace code editor feel */
div[data-testid="stTextArea"] textarea {
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}
/* Tighten up chat column spacing */
.chat-col [data-testid="stChatMessage"] {
    padding: 6px 0;
}
</style>
"""


# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        cfg = json.load(open(CONFIG_FILE))
        cfg.setdefault("student_overrides", {})
        return cfg
    return {"help_level": 2, "teacher_password": DEFAULT_PASSWORD, "student_overrides": {}}


def save_config(cfg: dict):
    json.dump(cfg, open(CONFIG_FILE, "w"), indent=2, ensure_ascii=False)


def get_effective_help_level(student_id: str) -> int:
    cfg = load_config()
    return cfg["student_overrides"].get(student_id, cfg.get("help_level", 2))


# ──────────────────────────────────────────────
# SESSIONS  (sessions.json)
# New format per student:
#   { student_id, completed_scenarios[], current{}, history[] }
# ──────────────────────────────────────────────
def load_sessions() -> dict:
    if os.path.exists(SESSIONS_FILE):
        return json.load(open(SESSIONS_FILE))
    return {}


def save_sessions(sessions: dict):
    json.dump(sessions, open(SESSIONS_FILE, "w"), indent=2, ensure_ascii=False)


def _default_student() -> dict:
    return {"completed_scenarios": [], "current": None, "history": []}


def get_student_data(student_id: str) -> dict:
    sessions = load_sessions()
    data = sessions.get(student_id, {})
    # Migrate old flat format
    if data and "completed_scenarios" not in data:
        completed = [data["scenario_id"]] if data.get("status") == "done" and data.get("scenario_id") else []
        return {
            **_default_student(),
            "student_id": student_id,
            "completed_scenarios": completed,
            "current": data if data.get("status") == "active" else None,
            "history": [data] if data.get("status") == "done" else [],
        }
    return data or {"student_id": student_id, **_default_student()}


def get_completed_scenarios(student_id: str) -> list:
    return get_student_data(student_id).get("completed_scenarios", [])


def register_session(student_id: str, scenario_id: str, scenario_name: str, help_level: int):
    sessions = load_sessions()
    student_data = get_student_data(student_id)
    student_data["student_id"] = student_id
    student_data["current"] = {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "help_level": help_level,
        "hint_count": 0,
        "score": None,
        "start_time": datetime.now().isoformat(timespec="seconds"),
        "last_active": datetime.now().isoformat(timespec="seconds"),
        "status": "active",
    }
    sessions[student_id] = student_data
    save_sessions(sessions)


def update_session_current(student_id: str, updates: dict):
    sessions = load_sessions()
    if student_id in sessions and sessions[student_id].get("current"):
        sessions[student_id]["current"].update(updates)
        sessions[student_id]["current"]["last_active"] = datetime.now().isoformat(timespec="seconds")
        save_sessions(sessions)


def complete_session(student_id: str, score: int, hint_count: int):
    sessions = load_sessions()
    student_data = sessions.get(student_id, get_student_data(student_id))
    current = student_data.get("current") or {}
    scenario_id = current.get("scenario_id")

    history_entry = {
        **current,
        "score": score,
        "hint_count": hint_count,
        "status": "done",
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }
    student_data.setdefault("history", []).append(history_entry)

    if scenario_id and scenario_id not in student_data.get("completed_scenarios", []):
        student_data.setdefault("completed_scenarios", []).append(scenario_id)

    student_data["current"] = None
    sessions[student_id] = student_data
    save_sessions(sessions)


# ──────────────────────────────────────────────
# CHAT LOG  (Results/)
# ──────────────────────────────────────────────
def save_chat_log(student_id, scenario_name, help_level, chat_history, score, hint_count):
    results_dir = "Results"
    os.makedirs(results_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(results_dir, f"session_{student_id}_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== Coding Tutor – C/C++ Session Log ===\n")
        f.write(f"Student ID  : {student_id}\n")
        f.write(f"Scenario    : {scenario_name}\n")
        f.write(f"Help Level  : {help_level} – {LEVEL_LABELS.get(help_level, '?')}\n")
        f.write(f"Hints Used  : {hint_count}\n")
        f.write(f"Final Score : {score if score is not None else 'N/A'}/100\n")
        f.write(f"Saved At    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 45 + "\n\n")
        for msg in chat_history:
            role = "Student" if msg["role"] == "user" else "Tutor  "
            f.write(f"[{role}]\n{msg['content']}\n\n")
    return path


# ──────────────────────────────────────────────
# GRAPH RUNNER
# ──────────────────────────────────────────────
def run_graph(app, state):
    latest_state = state
    new_messages = []
    seen = set()
    for node_update in app.stream(state):
        for _, node_dict in node_update.items():
            for msg in node_dict.get("messages", []):
                if type(msg).__name__ in ("AIMessage", "SystemMessage"):
                    msg_id = (
                        getattr(msg, "id", None)
                        or msg.additional_kwargs.get("id")
                        or hash(msg.content)
                    )
                    if msg_id not in seen:
                        new_messages.append(msg)
                        seen.add(msg_id)
            latest_state = node_dict
    return latest_state, new_messages


# ──────────────────────────────────────────────
# SESSION STATE INIT
# ──────────────────────────────────────────────
def init_session():
    defaults = {
        "page": "landing",
        "teacher_auth": False,
        "student_started": False,
        "student_id": "",
        "graph_app": None,
        "graph_state": None,
        "chat_history": [],
        "log_saved": False,
        "_pending_chat": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ──────────────────────────────────────────────
# PAGE: LANDING
# ──────────────────────────────────────────────
def page_landing():
    st.markdown(
        "<h1 style='text-align:center'>🎓 Coding Tutor – C/C++</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:gray'>מערכת מבחן ולמידה מבוססת AI לקורסי תכנות</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### מי את/ה?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("👨‍🏫  מרצה", use_container_width=True, type="secondary"):
                st.session_state.page = "teacher"
                st.rerun()
        with c2:
            if st.button("👨‍🎓  סטודנט", use_container_width=True, type="primary"):
                st.session_state.page = "student"
                st.rerun()


# ──────────────────────────────────────────────
# PAGE: TEACHER
# ──────────────────────────────────────────────
def page_teacher():
    st.title("👨‍🏫 Teacher Dashboard")
    cfg = load_config()

    if not st.session_state.teacher_auth:
        st.markdown("### כניסת מרצה")
        pwd = st.text_input("סיסמא", type="password", key="teacher_pwd_input")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("כניסה", type="primary"):
                if pwd == cfg.get("teacher_password", DEFAULT_PASSWORD):
                    st.session_state.teacher_auth = True
                    st.rerun()
                else:
                    st.error("סיסמא שגויה")
        with c2:
            if st.button("← חזרה"):
                st.session_state.page = "landing"
                st.rerun()
        return

    st.success("מחובר כמרצה ✅")
    tab1, tab2, tab3 = st.tabs(["⚙️ הגדרות כלליות", "👥 ניהול סטודנטים", "📋 לוגים"])

    # ─ Tab 1: Global settings ─
    with tab1:
        st.markdown("### רמת עזרה ברירת מחדל")
        current_level = cfg.get("help_level", 2)
        new_level = st.radio(
            "בחר רמה:",
            options=[1, 2, 3],
            index=current_level - 1,
            format_func=lambda x: f"רמה {x} – {LEVEL_LABELS[x]}  |  {LEVEL_DESCRIPTIONS[x]}",
        )
        st.markdown("### שינוי סיסמא")
        new_pwd = st.text_input("סיסמא חדשה (ריק = שמור נוכחית)", type="password")
        if st.button("💾 שמור הגדרות", type="primary"):
            cfg["help_level"] = new_level
            if new_pwd:
                cfg["teacher_password"] = new_pwd
            save_config(cfg)
            st.success(f"✅ נשמר! ברירת מחדל: רמה {new_level} – {LEVEL_LABELS[new_level]}")

    # ─ Tab 2: Student management ─
    with tab2:
        sessions = load_sessions()
        if not sessions:
            st.info("אין עדיין סטודנטים במערכת.")
        else:
            st.markdown("### סיכום סטודנטים")
            rows = []
            for sid, raw in sessions.items():
                data = get_student_data(sid)
                current = data.get("current")
                history = data.get("history", [])
                eff_lvl = get_effective_help_level(sid)
                override_mark = " ✏️" if sid in cfg.get("student_overrides", {}) else ""
                scores_str = ", ".join(
                    [f"{h.get('score', '?')}" for h in history if h.get("score") is not None]
                ) or "—"
                rows.append({
                    "ת.ז": sid,
                    "שאלות שנענו": len(data.get("completed_scenarios", [])),
                    "ציונים": scores_str,
                    "שאלה נוכחית": current.get("scenario_name", "—") if current else "—",
                    "סטטוס": "🔵 פעיל" if current else "✅ סיים",
                    "רמת עזרה": f"{eff_lvl} – {LEVEL_LABELS.get(eff_lvl, '?')}{override_mark}",
                })
            st.dataframe(rows, use_container_width=True)

            st.markdown("---")
            st.markdown("### שינוי רמת עזרה לסטודנט")
            selected_sid = st.selectbox("בחר סטודנט:", list(sessions.keys()), key="sel_student")
            cur_override = cfg.get("student_overrides", {}).get(selected_sid, cfg.get("help_level", 2))
            override_note = " (override)" if selected_sid in cfg.get("student_overrides", {}) else " (ברירת מחדל)"

            new_sid_level = st.radio(
                f"רמה עבור {selected_sid}{override_note}:",
                options=[1, 2, 3],
                index=cur_override - 1,
                format_func=lambda x: f"רמה {x} – {LEVEL_LABELS[x]}",
                key="student_level_radio",
            )
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("💾 שמור", type="primary"):
                    cfg.setdefault("student_overrides", {})[selected_sid] = new_sid_level
                    save_config(cfg)
                    update_session_current(selected_sid, {"help_level": new_sid_level})
                    st.success(f"✅ {selected_sid} → רמה {new_sid_level}")
                    st.rerun()
            with c2:
                if st.button("🔄 אפס לברירת מחדל"):
                    overrides = cfg.get("student_overrides", {})
                    if selected_sid in overrides:
                        del overrides[selected_sid]
                        save_config(cfg)
                        st.success(f"אופס לרמה {cfg.get('help_level', 2)}")
                        st.rerun()
                    else:
                        st.info("אין override פעיל.")

            # Per-student history detail
            student_data = get_student_data(selected_sid)
            history = student_data.get("history", [])
            if history:
                st.markdown(f"#### היסטוריה של {selected_sid}")
                hist_rows = [
                    {
                        "שאלה": h.get("scenario_name", h.get("scenario_id", "?")),
                        "רמז": h.get("hint_count", 0),
                        "ציון": h.get("score", "—"),
                        "תאריך": h.get("completed_at", "")[:16].replace("T", " "),
                    }
                    for h in history
                ]
                st.dataframe(hist_rows, use_container_width=True)

    # ─ Tab 3: Logs ─
    with tab3:
        st.markdown("### לוגים")
        st.caption(
            "קבצים: `Results/session_{ת.ז}_{תאריך}.txt`  |  "
            "מכיל: מזהה סטודנט, שאלה, רמת עזרה, רמזים, ציון, כל שיחת הצ'אט."
        )
        results_dir = "Results"
        if os.path.exists(results_dir):
            logs = sorted(os.listdir(results_dir), reverse=True)
            if logs:
                selected_log = st.selectbox("בחר לוג:", logs)
                if st.button("📄 פתח"):
                    with open(os.path.join(results_dir, selected_log), encoding="utf-8") as f:
                        st.text_area("", f.read(), height=400)
            else:
                st.info("אין עדיין לוגים.")
        else:
            st.info("תיקיית Results תיווצר אחרי הגשה ראשונה.")

    st.markdown("---")
    if st.button("🚪 התנתקות"):
        st.session_state.teacher_auth = False
        st.session_state.page = "landing"
        st.rerun()


# ──────────────────────────────────────────────
# PAGE: STUDENT
# ──────────────────────────────────────────────
def page_student():
    # ── Enter student ID ──
    if not st.session_state.student_started:
        st.title("👨‍🎓 Coding Tutor – C/C++")
        st.markdown("---")
        student_id = st.text_input("הזן מספר תעודת זהות:")
        c1, c2 = st.columns([1, 5])
        with c1:
            start = st.button("התחל", type="primary")
        with c2:
            if st.button("← חזרה"):
                st.session_state.page = "landing"
                st.rerun()

        if start and student_id.strip():
            sid = student_id.strip()
            effective_level = get_effective_help_level(sid)
            completed = get_completed_scenarios(sid)

            with st.spinner("טוען מטלה..."):
                sim = CodingTutorSim(
                    student_id=sid,
                    help_level=effective_level,
                    completed_scenarios=completed,
                )
                app = sim.compile()
                state = sim.get_initial_state()
                new_state, new_msgs = run_graph(app, state)

            scenario_id = new_state.get("scenario_id", "unknown")
            scenario_name = new_state.get("scenario_data", {}).get("name", scenario_id)
            register_session(sid, scenario_id, scenario_name, effective_level)

            st.session_state.graph_app = app
            st.session_state.graph_state = new_state
            st.session_state.student_id = sid
            st.session_state.student_started = True
            st.session_state.log_saved = False
            st.session_state.chat_history = []

            for msg in new_msgs:
                st.session_state.chat_history.append({"role": "assistant", "content": msg.content})

            st.rerun()
        return

    # ── Active session ──
    gs = st.session_state.graph_state
    effective_level = get_effective_help_level(st.session_state.student_id)
    is_done = gs and gs.get("current_phase") == "done"

    # Sync help level in graph state
    if gs:
        gs["help_level"] = effective_level

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f"**סטודנט:** `{st.session_state.student_id}`")
        st.markdown(f"**רמת עזרה:** {effective_level} – {LEVEL_LABELS.get(effective_level, '?')}")
        if gs:
            st.markdown(f"**שאלות שנשאלו:** {gs.get('hint_count', 0)}")
            phase_labels = {"chat": "💬 שיחה", "evaluation": "🔍 הערכה", "done": "🏁 הסתיים"}
            st.markdown(f"**שלב:** {phase_labels.get(gs.get('current_phase', 'chat'), '')}")
            if is_done:
                st.markdown(f"**ציון:** {gs.get('score', 0)}/100")

        completed = get_completed_scenarios(st.session_state.student_id)
        if completed:
            st.markdown(f"**שאלות שהושלמו:** {len(completed)}")

        # Help level increase button
        if not is_done and effective_level < 3:
            st.markdown("---")
            next_lvl = effective_level + 1
            if st.button(
                f"🆘 בקש עזרה נוספת → רמה {next_lvl}",
                use_container_width=True,
                help=f"יעלה את רמת העזרה ל-{LEVEL_LABELS[next_lvl]}",
            ):
                cfg = load_config()
                cfg.setdefault("student_overrides", {})[st.session_state.student_id] = next_lvl
                save_config(cfg)
                update_session_current(st.session_state.student_id, {"help_level": next_lvl})
                gs["help_level"] = next_lvl
                st.session_state.graph_state = gs
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": (
                        f"ℹ️ **רמת העזרה עלתה לרמה {next_lvl} – {LEVEL_LABELS[next_lvl]}.**  \n"
                        f"{LEVEL_DESCRIPTIONS[next_lvl]}"
                    ),
                })
                st.rerun()

        st.markdown("---")
        if st.button("🚪 סיום סשן", use_container_width=True):
            st.session_state.student_started = False
            st.session_state.graph_state = None
            st.session_state.graph_app = None
            st.session_state.chat_history = []
            st.session_state.log_saved = False
            st.session_state.student_id = ""
            st.session_state.page = "landing"
            st.rerun()

    # ── Done: save log once ──
    if is_done:
        if not st.session_state.log_saved:
            scenario_name = gs.get("scenario_data", {}).get("name", "unknown")
            save_chat_log(
                st.session_state.student_id,
                scenario_name,
                gs.get("help_level", 2),
                st.session_state.chat_history,
                gs.get("score", 0),
                gs.get("hint_count", 0),
            )
            complete_session(
                st.session_state.student_id,
                gs.get("score", 0),
                gs.get("hint_count", 0),
            )
            st.session_state.log_saved = True

        st.title("🎓 Coding Tutor – C/C++")
        st.success(f"🏆 סשן הסתיים! ציון: {gs.get('score', 0)}/100")
        st.info("ניתן לסגור או לחזור דרך 'סיום סשן' בסרגל הצד.")
        st.markdown("### שיחה שהייתה")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        st.stop()

    # ── IDE + Chat side-by-side ──
    st.markdown(IDE_CSS, unsafe_allow_html=True)
    st.title("🎓 Coding Tutor – C/C++")

    col_code, col_chat = st.columns([1, 1], gap="medium")

    # ─ Left: code editor ─
    with col_code:
        st.markdown("#### ✏️ עורך קוד")
        code = st.text_area(
            label="",
            height=430,
            key="live_code",
            placeholder=CODE_PLACEHOLDER,
            label_visibility="collapsed",
        )
        if st.button("✅ הגש קוד", type="primary", use_container_width=True, disabled=is_done):
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

    # ─ Right: chat ─
    with col_chat:
        st.markdown("#### 💬 שאל את המורה")

        # Scrollable chat history
        with st.container(height=370):
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Chat form (clears input after send)
        with st.form("chat_form", clear_on_submit=True, border=False):
            c_inp, c_btn = st.columns([5, 1])
            with c_inp:
                prompt = st.text_input(
                    "",
                    placeholder="שאל שאלה על המטלה...",
                    label_visibility="collapsed",
                    disabled=is_done,
                )
            with c_btn:
                send = st.form_submit_button("שלח", use_container_width=True, disabled=is_done)

        if send and prompt.strip():
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            gs["messages"] = gs.get("messages", []) + [HumanMessage(content=prompt)]

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


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Coding Tutor – C/C++",
    page_icon="🎓",
    layout="wide",
)

init_session()

if st.session_state.page == "landing":
    page_landing()
elif st.session_state.page == "teacher":
    page_teacher()
elif st.session_state.page == "student":
    page_student()
