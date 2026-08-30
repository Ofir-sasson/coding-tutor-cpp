"""
Teacher Dashboard — C/C++ Coding Tutor
Run with: streamlit run teacher_app.py
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
        "Coding Tutor – C/C++ | המכללה האקדמית להנדסה ירושלים"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col = st.columns([1, 1, 1])[1]
    with col:
        cfg = load_config()
        pwd = st.text_input("סיסמא", type="password")
        if st.button("כניסה", type="primary", use_container_width=True):
            if pwd == cfg.get("teacher_password", DEFAULT_PASSWORD):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("סיסמא שגויה")


# ── Dashboard ─────────────────────────────────────────────────────────────────

def screen_dashboard():
    render_dark_mode_toggle()
    st.title("👨‍🏫 Teacher Dashboard")
    st.success("מחובר ✅")

    tab1, tab2, tab3 = st.tabs(["⚙️ הגדרות", "👥 סטודנטים", "📋 לוגים"])

    cfg = load_config()

    # ─ Tab 1: Global settings ─────────────────────────────────────────────────
    with tab1:
        st.markdown("### רמת עזרה")
        st.caption(
            "כל שאלה של סטודנט מתחילה אוטומטית ברמה 1 (מנחה בלבד). אם הסטודנט "
            "מציין שלא הבין, הרמה עולה אוטומטית עבור אותה שאלה בלבד — עד רמה 3. "
            "שאלה חדשה תמיד מתחילה שוב מרמה 1. אין הגדרת רמה ידנית."
        )

        st.markdown("---")
        st.markdown("### שינוי סיסמא")
        new_pwd = st.text_input("סיסמא חדשה (ריק = שמור נוכחית)", type="password")

        if st.button("💾 שמור הגדרות", type="primary"):
            if new_pwd:
                cfg["teacher_password"] = new_pwd
                save_config(cfg)
            st.success("✅ נשמר!")

        st.markdown("---")
        st.markdown("### מידע על השאלות")
        st.markdown("""
| נושא | ID |
|------|-----|
| Bit Manipulation | `bit_ops` |
| String Utils (ללא string.h) | `strings_no_lib` |
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
            st.info("אין עדיין סטודנטים שנכנסו למערכת.")
        else:
            st.markdown("### סיכום כל הסטודנטים")

            rows = []
            for sid in sessions:
                data = get_student_data(sid)
                current = data.get("current")
                history = data.get("history", [])
                scores = [h["score"] for h in history if h.get("score") is not None]
                avg_score = round(sum(scores) / len(scores), 1) if scores else "—"
                rows.append({
                    "ת.ז": sid,
                    "שאלות שנענו": len(data.get("completed_scenarios", [])),
                    "ממוצע ציונים": avg_score,
                    "ציונים": ", ".join(str(s) for s in scores) or "—",
                    "שאלה נוכחית": current.get("scenario_name", "—") if current else "—",
                    "סטטוס": "🔵 פעיל" if current else "✅ סיים",
                })
            st.dataframe(rows, use_container_width=True)

            st.markdown("---")
            st.markdown("### ניהול סטודנט")
            selected_sid = st.selectbox("בחר סטודנט:", list(sessions.keys()))
            data = get_student_data(selected_sid)

            st.markdown(f"#### שאלות שהושלמו — {selected_sid}")
            completed = data.get("completed_scenarios", [])
            if completed:
                for sc_id in completed:
                    st.markdown(f"- `{sc_id}`")
            else:
                st.info("עדיין לא השלים שאלות.")

            history = data.get("history", [])
            if history:
                st.markdown(f"#### היסטוריית סשנים — {selected_sid}")
                hist_rows = [
                    {
                        "שאלה": h.get("scenario_name", h.get("scenario_id", "?")),
                        "רמזים": h.get("hint_count", 0),
                        "ציון": h.get("score", "—"),
                        "תאריך": h.get("completed_at", "")[:16].replace("T", " "),
                    }
                    for h in history
                ]
                st.dataframe(hist_rows, use_container_width=True)

    # ─ Tab 3: Logs ────────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### לוגים של סשנים")
        st.caption(
            "**מיקום:** `Results/session_{ת.ז}_{תאריך}.txt`  \n"
            "**תוכן:** מזהה סטודנט, שאלה, רמת עזרה, מספר רמזים, ציון סופי, שיחת צ'אט מלאה."
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
                    f"⚠️ {legacy_count} קבצים בתיקייה אינם בפורמט לוג-בחינה תקני "
                    "(שאריות מגרסאות/כלים ישנים יותר) — לא מוצגים כאן."
                )
            if logs:
                col_sel, col_filter = st.columns([2, 1])
                with col_filter:
                    filter_sid = st.text_input("סנן לפי ת.ז (ריק = הכל):", key="log_filter")
                filtered_logs = [l for l in logs if not filter_sid or filter_sid in l]
                with col_sel:
                    selected_log = st.selectbox("בחר לוג:", filtered_logs or ["(אין תוצאות)"])
                if filtered_logs and st.button("📄 פתח לוג"):
                    import os as _os
                    path = _os.path.join(results_dir, selected_log)
                    if _os.path.exists(path):
                        with open(path, encoding="utf-8") as f:
                            st.text_area("", f.read(), height=450)
            else:
                st.info("אין עדיין לוגים.")
        else:
            st.info("תיקיית Results תיווצר אחרי ההגשה הראשונה.")

    st.markdown("---")
    if st.button("🚪 התנתקות"):
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
