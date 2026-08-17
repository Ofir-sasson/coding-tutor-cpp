"""Shared helpers used by both student_app.py and teacher_app.py."""

import os
import re
import json
from datetime import datetime
import streamlit as st
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

# ── Dark mode ────────────────────────────────────────────────────────────────
# Streamlit has no runtime theme-switch API — this overrides its own dark-theme
# colors (#0E1117 / #262730 / #FAFAFA) via CSS so it looks native either way.
DARK_CSS = """
<style>
.stApp { background-color: #0E1117; color: #FAFAFA; }
.stApp p, .stApp span, .stApp label, .stApp li, .stApp div,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color: #FAFAFA; }
[data-testid="stSidebar"] { background-color: #262730; }
[data-testid="stSidebar"] * { color: #FAFAFA !important; }
[data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input { background-color: #1a1c24 !important; color: #FAFAFA !important; }
div[data-testid="stTextArea"] textarea::placeholder { color: #7d818c !important; opacity: 1 !important; }
div[data-testid="stChatMessage"] { background-color: #1a1c24; }
[data-testid="stExpander"] { background-color: #1a1c24; border: 1px solid #41434c; }
/* Streamlit's own button styles (esp. inside the sidebar, and buttons with a
   `help=` tooltip) win the specificity fight against a plain ".stButton>button"
   rule and keep their default light background — with white text forced on
   top by the rules above, that reads as an empty white box. Cover both the
   class-based and data-testid-based button markup, !important, no ">"
   child-combinator so nested tooltip wrappers don't break the match. */
.stButton button, [data-testid^="stBaseButton"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border: 1px solid #41434c !important;
}
hr { border-color: #41434c; }
/* Fenced ```code``` blocks (e.g. task descriptions, part history) got a dark
   text color from the ".stApp div/span" rules above but kept their default
   light background — that combo renders as an invisible white-on-white box.
   Force a dark background through the whole block so the (already-white)
   text is actually legible. */
[data-testid="stCodeBlock"] { background-color: #1a1c24 !important; border-radius: 6px; }
[data-testid="stCodeBlock"] * { background-color: transparent !important; color: #FAFAFA !important; }
.stApp pre { background-color: #1a1c24 !important; }
.stApp pre * { background-color: transparent !important; color: #FAFAFA !important; }
/* st.info/success/error/warning (score, test results, sidebar phase) use a
   translucent tint over whatever's behind them rather than a fixed color —
   over the dark app background that lands as near-black-on-near-black.
   Give them an explicit opaque dark surface instead of relying on that
   blending, so it's readable regardless of how Streamlit tints it. */
[data-testid="stAlert"] { background-color: #1a1c24 !important; }
[data-testid="stAlert"] * { color: #FAFAFA !important; background-color: transparent !important; }
</style>
"""

# Shrinks the default (fairly wide) Streamlit sidebar so the two-column code/
# chat layout gets more room. Applied regardless of dark/light mode.
LAYOUT_CSS = """
<style>
[data-testid="stSidebar"] { width: 230px !important; min-width: 230px !important; max-width: 230px !important; }
</style>
"""


def render_dark_mode_toggle():
    """Sidebar toggle for a runtime dark theme; injects CSS overrides when on."""
    st.markdown(LAYOUT_CSS, unsafe_allow_html=True)
    dark = st.sidebar.toggle("🌙 מצב כהה", key="dark_mode")
    if dark:
        st.markdown(DARK_CSS, unsafe_allow_html=True)


# ── Config ───────────────────────────────────────────────────────────────────

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


# ── Sessions (sessions.json) ──────────────────────────────────────────────────
# Per-student format:
#   { student_id, completed_scenarios[], current{...} | None, history[...] }

def load_sessions() -> dict:
    if os.path.exists(SESSIONS_FILE):
        return json.load(open(SESSIONS_FILE))
    return {}


def save_sessions(sessions: dict):
    json.dump(sessions, open(SESSIONS_FILE, "w"), indent=2, ensure_ascii=False)


def _default_student(student_id: str) -> dict:
    return {"student_id": student_id, "completed_scenarios": [], "current": None, "history": []}


def get_student_data(student_id: str) -> dict:
    data = load_sessions().get(student_id, {})
    # Migrate from old flat format
    if data and "completed_scenarios" not in data:
        completed = [data["scenario_id"]] if data.get("status") == "done" and data.get("scenario_id") else []
        return {
            **_default_student(student_id),
            "completed_scenarios": completed,
            "current": data if data.get("status") == "active" else None,
            "history": [data] if data.get("status") == "done" else [],
        }
    return data or _default_student(student_id)


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
    student_data = sessions.get(student_id) or get_student_data(student_id)
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


# ── Chat log (Results/) ───────────────────────────────────────────────────────
# Filename shape written below: session_{student_id}_{YYYYMMDD}_{HHMMSS}.txt
# Older tools wrote to the same folder with different shapes — the CLI
# (main.py) used "session_{YYYYMMDD}_{HHMMSS}.txt" (no student id at all),
# and an earlier prototype wrote "simulation_log_*.txt". Both are unrelated
# to this app's real exam sessions; is_real_session_log() tells them apart
# so the teacher dashboard's Logs tab only lists genuine student sessions.
SESSION_LOG_RE = re.compile(r"^session_(?P<student_id>[^_]+)_\d{8}_\d{6}\.txt$")


def is_real_session_log(filename: str) -> bool:
    return bool(SESSION_LOG_RE.match(filename))


def save_chat_log(student_id, scenario_name, help_level, chat_history, score, hint_count) -> str:
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


# ── Graph runner ──────────────────────────────────────────────────────────────

def run_graph(app, state):
    latest_state = state
    new_messages = []
    seen = set()
    for node_update in app.stream(state):
        for _, node_dict in node_update.items():
            if not node_dict:
                continue
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


# ── Session builder ───────────────────────────────────────────────────────────

def start_student_session(student_id: str):
    """
    Build CodingTutorSim, run first graph step (task presentation),
    register session. Returns (graph_app, graph_state, initial_chat_messages).
    """
    effective_level = get_effective_help_level(student_id)
    completed = get_completed_scenarios(student_id)

    sim = CodingTutorSim(
        student_id=student_id,
        help_level=effective_level,
        completed_scenarios=completed,
    )
    app = sim.compile()
    state = sim.get_initial_state()
    new_state, new_msgs = run_graph(app, state)

    scenario_id = new_state.get("scenario_id", "unknown")
    scenario_name = new_state.get("scenario_data", {}).get("name", scenario_id)
    register_session(student_id, scenario_id, scenario_name, effective_level)

    chat_msgs = [{"role": "assistant", "content": m.content} for m in new_msgs]
    return app, sim.nodes, new_state, chat_msgs
