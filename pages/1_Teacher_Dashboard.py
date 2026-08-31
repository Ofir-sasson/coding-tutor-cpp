"""
Teacher Dashboard — C/C++ Coding Tutor
Page of the multipage app rooted at student_app.py — reachable from its
sidebar nav, sharing the same process/filesystem so it can see student data.
Default password: teacher123
"""

import os
import streamlit as st
from app_shared import (
    DEFAULT_PASSWORD,
    load_config, save_config,
    load_sessions, get_student_data,
    render_dark_mode_toggle, is_real_session_log,
)


# ── Session state ─────────────────────────────────────────────────────────────

def init():
    if "auth" not in st.session_state:
        st.session_state.auth = False


# ── Login screen ──────────────────────────────────────────────────────────────

def screen_login():
    render_dark_mode_toggle()
    st.markdown(
        "<h1 style='text-align:center'>👨‍🏫 Teacher Dashboard</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:gray'>"
        "Coding Tutor – C/C++ | Jerusalem College of Engineering"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col = st.columns([1, 1, 1])[1]
    with col:
        cfg = load_config()
        pwd = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if pwd == cfg.get("teacher_password", DEFAULT_PASSWORD):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Incorrect password")


# ── Dashboard ─────────────────────────────────────────────────────────────────

def screen_dashboard():
    render_dark_mode_toggle()
    st.title("👨‍🏫 Teacher Dashboard")
    st.success("Logged in ✅")

    tab1, tab2, tab3 = st.tabs(["⚙️ Settings", "👥 Students", "📋 Logs"])

    cfg = load_config()

    # ─ Tab 1: Global settings ─────────────────────────────────────────────────
    with tab1:
        st.markdown("### Help Level")
        st.caption(
            "Every student question automatically starts at level 1 (guided only). "
            "If the student indicates they didn't understand, the level automatically "
            "rises for that question only — up to level 3. A new question always "
            "starts again from level 1. There is no manual level setting."
        )

        st.markdown("---")
        st.markdown("### Change Password")
        new_pwd = st.text_input("New password (empty = keep current)", type="password")

        if st.button("💾 Save Settings", type="primary"):
            if new_pwd:
                cfg["teacher_password"] = new_pwd
                save_config(cfg)
            st.success("✅ Saved!")

        st.markdown("---")
        st.markdown("### Question Info")
        st.markdown("""
| Topic | ID |
|------|-----|
| Bit Manipulation | `bit_ops` |
| String Utils (without string.h) | `strings_no_lib` |
| Pointer Arithmetic | `pointer_arithmetic` |
| Dynamic 2D Array | `dynamic_2d_array` |
| File I/O | `file_io` |
| Function Pointers | `func_pointers` |
| Linked List | `linked_list` |
| Classes & Inheritance | `cpp_class_inherit` |
| Operator Overloading | `cpp_operator_overload` |
| Templates | `cpp_template` |
| STL (Word Frequency) | `cpp_stl` |
| Smart Pointers | `cpp_smart_ptrs` |
""")

    # ─ Tab 2: Student management ──────────────────────────────────────────────
    with tab2:
        sessions = load_sessions()

        if not sessions:
            st.info("No students have logged into the system yet.")
        else:
            st.markdown("### Summary of All Students")

            rows = []
            for sid in sessions:
                data = get_student_data(sid)
                current = data.get("current")
                history = data.get("history", [])
                scores = [h["score"] for h in history if h.get("score") is not None]
                avg_score = round(sum(scores) / len(scores), 1) if scores else "—"
                rows.append({
                    "ID": sid,
                    "Questions Answered": len(data.get("completed_scenarios", [])),
                    "Average Score": avg_score,
                    "Scores": ", ".join(str(s) for s in scores) or "—",
                    "Current Question": current.get("scenario_name", "—") if current else "—",
                    "Status": "🔵 Active" if current else "✅ Finished",
                })
            st.dataframe(rows, use_container_width=True)

            st.markdown("---")
            st.markdown("### Student Management")
            selected_sid = st.selectbox("Select student:", list(sessions.keys()))
            data = get_student_data(selected_sid)

            st.markdown(f"#### Completed Questions — {selected_sid}")
            completed = data.get("completed_scenarios", [])
            if completed:
                for sc_id in completed:
                    st.markdown(f"- `{sc_id}`")
            else:
                st.info("Hasn't completed any questions yet.")

            history = data.get("history", [])
            if history:
                st.markdown(f"#### Session History — {selected_sid}")
                hist_rows = [
                    {
                        "Question": h.get("scenario_name", h.get("scenario_id", "?")),
                        "Hints": h.get("hint_count", 0),
                        "Score": h.get("score", "—"),
                        "Date": h.get("completed_at", "")[:16].replace("T", " "),
                    }
                    for h in history
                ]
                st.dataframe(hist_rows, use_container_width=True)

    # ─ Tab 3: Logs ────────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### Session Logs")
        st.caption(
            "**Location:** `Results/session_{id}_{date}.txt`  \n"
            "**Content:** student ID, question, help level, number of hints, final score, full chat transcript."
        )
        results_dir = "Results"
        if os.path.exists(results_dir):
            all_files = os.listdir(results_dir)
            legacy_count = sum(
                1 for f in all_files if f.endswith(".txt") and not is_real_session_log(f)
            )
            logs = sorted((f for f in all_files if is_real_session_log(f)), reverse=True)
            if legacy_count:
                st.caption(
                    f"⚠️ {legacy_count} files in this folder are not in the standard exam-log format "
                    "(leftovers from older versions/tools) — not shown here."
                )
            if logs:
                col_sel, col_filter = st.columns([2, 1])
                with col_filter:
                    filter_sid = st.text_input("Filter by ID (empty = all):", key="log_filter")
                filtered_logs = [l for l in logs if not filter_sid or filter_sid in l]
                with col_sel:
                    selected_log = st.selectbox("Select log:", filtered_logs or ["(no results)"])
                if filtered_logs and st.button("📄 Open Log"):
                    import os as _os
                    path = _os.path.join(results_dir, selected_log)
                    if _os.path.exists(path):
                        with open(path, encoding="utf-8") as f:
                            st.text_area("Log contents", f.read(), height=450)
            else:
                st.info("No logs yet.")
        else:
            st.info("The Results folder will be created after the first submission.")

    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()


# ── Entry point ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Teacher Dashboard – C/C++",
    page_icon="👨‍🏫",
    layout="wide",
)

init()

if not st.session_state.auth:
    screen_login()
else:
    screen_dashboard()
