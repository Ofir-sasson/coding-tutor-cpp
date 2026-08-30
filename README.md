# Coding Tutor – C/C++

An AI-tutored, auto-graded C/C++ exam environment for a university course. Students
solve C/C++ programming tasks in a browser IDE, can ask an LLM tutor for help along
the way, get their code compiled and tested automatically, and receive a score.
A separate teacher dashboard shows every student's progress and lets the instructor
read the full chat/session logs.

It's two Streamlit apps sharing one backend:

- **`student_app.py`** — the exam UI students use.
- **`teacher_app.py`** — the password-protected dashboard the instructor uses.
- **`app_shared.py`** — everything both apps need in common (config, session
  bookkeeping, log writing, dark mode, the LangGraph runner).
- **`production_sim/`** — the actual tutoring/grading engine (LangGraph state
  machine, the scenario bank, the LLM prompts, the C/C++ auto-grader).

There is no separate backend server — Streamlit *is* the server, and each app
talks directly to a local [Ollama](https://ollama.com) model and to `gcc`/`g++`
on the same machine.

---

## How a session works

1. A student opens `student_app.py`, types their student ID, and clicks **התחל
   בחינה** (Start Exam).
2. `start_student_session()` (in `app_shared.py`) builds a `CodingTutorSim`
   (`production_sim/graph.py`), which:
   - picks a scenario for that student via `ScenarioManager` (deterministic
     per-student, skips scenarios they've already completed — see
     [Scenario selection](#scenario-selection) below),
   - runs the LangGraph once so the tutor posts its opening greeting.
3. The student works through the task in a code editor next to a chat panel,
   asking the tutor questions as needed (see [The tutor and its help
   levels](#the-tutor-and-its-help-levels)).
4. Code is compiled and run against a hidden test harness
   (`production_sim/auto_tester.py`) either per-part (multi-part scenarios) or
   as one final submission that an LLM evaluator grades
   (single-submission scenarios).
5. On completion, a score is computed, a full transcript is written to
   `Results/`, and `sessions.json` is updated so the teacher dashboard and the
   student's next login both see it.

---

## The tutor and its help levels

The tutor node (`production_sim/agents.py: AgentNodes.tutor_node` /
`stream_tutor_response`) answers in one of three registers, enforced through
the system prompt and a post-hoc code-leak filter:

| Level | Name | Behavior |
|---|---|---|
| 1 | Strict | 1–2 short guiding questions. Never any code. |
| 2 | Guided | A short conceptual explanation in plain words. Still no code. |
| 3 | Supported | Full explanations with code examples allowed. |

**The level is fully automatic and resets per question — there is no manual
level selector anywhere in the app:**

- Every new question a student asks starts at **level 1**.
- If the student's next message indicates they didn't understand / need more
  help on that *same* question, the tutor escalates one level (capped at 3)
  for the next reply. A small local LLM call
  (`AgentNodes._classify_continuation`) reads the tutor's last reply and the
  student's new message and classifies it as `SAME` (still on this question)
  or `NEW` (a different question) — this uses the same Ollama model as the
  tutor itself, not a keyword match.
- Asking something new resets back to level 1, even mid-conversation.
- The chat panel shows a small "ℹ️ escalating to level X" notice whenever
  this happens, and the sidebar always shows the level in effect for the
  *current* question.

This logic lives in `AgentNodes.compute_question_level()` and is shared by
both the interactive Streamlit path (`stream_tutor_response`, called from
`student_app.py`'s chat handler) and the LangGraph `tutor_node` path (used
when the graph is driven via `run_graph()`, e.g. the very first greeting).

If a reply at level 1 or 2 accidentally contains code, `AgentNodes._chat()`
detects it (`_has_code`, a regex over common C/C++ constructs) and re-asks the
model once for a code-free rewrite before showing anything to the student.

Levels 1–2 wait for the full reply before showing it (so the code filter can
run); level 3 streams token-by-token via `st.write_stream`.

---

## Scenario selection

`ScenarioManager.get_scenario(student_id, exclude_ids)` (in
`production_sim/scenarios.py`) seeds Python's RNG from the sum of the
student ID's character codes, so **the same student always gets the same
sequence of scenarios**, but different students get different (pseudo-random)
ones — no two students are guaranteed the identical task, and a student can't
predict their next one. `exclude_ids` is the student's already-completed
scenario list (from `sessions.json`), so a student is never handed the same
scenario twice until they've cycled through all of them.

### Scenario bank (12 topics)

Each scenario is either **multi-part** (solved and auto-tested part by part,
with its own progress bar and per-part chat context) or **single-submission**
(one code box, submitted once, graded by an LLM evaluator against a written
checklist).

| ID | Topic | Parts | Notes |
|---|---|---|---|
| `bit_ops` | Bit Manipulation in C | 4 | |
| `strings_no_lib` | String Utilities Without `<string.h>` | 5 | `accumulate_code` |
| `pointer_arithmetic` | Pointer Arithmetic in C | 2 | |
| `dynamic_2d_array` | Dynamic 2D Array in C | 3 | |
| `file_io` | File I/O in C | — | single-submission |
| `func_pointers` | Function Pointers in C | 2 | |
| `linked_list` | Singly Linked List in C | 4 | `accumulate_code` |
| `cpp_class_inherit` | C++ Classes and Inheritance | 3 | |
| `cpp_operator_overload` | C++ Operator Overloading — Complex Numbers | 3 | `carry_forward_code` |
| `cpp_template` | C++ Generic Templates | 2 | |
| `cpp_stl` | C++ STL — Word Frequency Counter | — | single-submission |
| `cpp_smart_ptrs` | C++ Smart Pointers | — | single-submission |

The two multi-part flags change how parts relate to each other:

- **`accumulate_code`** — each part is a separate free function, and later
  parts' test harnesses call functions written in earlier parts (e.g.
  `my_strcpy` calling `my_strlen`). Passed parts' code is concatenated
  together before compiling the next part.
- **`carry_forward_code`** — parts build up *one* class/struct definition
  that can't be split across two declarations without a compile error, so
  instead the next part's editor is pre-filled with the code that just
  passed, letting the student extend it in place.
- Scenarios with neither flag have fully independent parts and can be
  answered in any order; the progress bar lets the student jump between any
  part they've already reached.

Each scenario dict carries: `dev_requirement` (the full task shown to a
single-submission student), `requirements` / `validation_criteria` (fed to
the LLM evaluator), and for multi-part scenarios a `parts` list, each part
with `title`, `description`, `setup` (C/C++ preamble — typedefs, reference
helpers the student shouldn't redefine), and `test_harness` (a hidden
`main()` that exercises the student's function(s) and prints `ALL_PASS` on
success).

---

## Auto-grading (`production_sim/auto_tester.py`)

For multi-part scenarios, clicking **▶️ בדוק קוד** (Check Code) does:

```
part["setup"]  +  student's code  +  part["test_harness"]
```

writes it to a temp `.c`/`.cpp` file, compiles with `gcc`/`g++
-std=c++17 -Wall`, runs the binary, and passes only if its stdout contains
`ALL_PASS`. Compiler errors and failed-assertion output are shown to the
student verbatim (path names scrubbed). **`gcc` and `g++` must be installed
and on `PATH`** for this to work — there's no sandboxing beyond a
subprocess timeout.

**🔎 בדוק תחביר בלבד** (Syntax check only) runs `-fsyntax-only`, no linking or
execution — lets a student catch typos without spending a full test attempt.

For single-submission scenarios, the submitted code isn't compiled at all —
it's graded by the same local LLM as a strict evaluator
(`AgentNodes.evaluator_node`) against the scenario's `requirements` /
`validation_criteria` text, returning `PASS`/`FAIL` plus a short critique.

---

## Scoring (`production_sim/helper.py`)

```
score = 100 (or 50 if the final submission failed)
        − 0.5 × (level-1 hints)
        − 1.0 × (level-2 hints)
        − 1.5 × (level-3 hints)
        − 1.0 × (failed compile/test runs)
```
clamped to `[0, 100]`. Every chat reply counts as one "hint" at whatever
level it was answered at (`hints_per_level`, tracked live in the graph
state) — so, deliberately, leaning on level-3 help costs more than asking
several level-1 questions. `score_breakdown_md()` renders this as the
markdown table shown to the student when they finish.

---

## Project structure

```
student_app.py          Student exam UI (ID entry → code editor + chat → result)
teacher_app.py           Password-protected teacher dashboard
app_shared.py            Shared config/session/log helpers used by both apps
requirements.txt         Python dependencies (Streamlit + LangChain/LangGraph/Ollama)
run_app.command           Double-clickable launcher for student_app.py (macOS)
teacher_config.json       { teacher_password } — only the dashboard password now
sessions.json             Per-student state: completed scenarios, active session, history
Results/                  One .txt transcript per completed session (see below)

production_sim/
  __init__.py             Exposes CodingTutorSim
  graph.py                CodingTutorSim: builds the LangGraph (router → tutor | evaluator)
  state.py                TutorState TypedDict — the graph's shared state shape
  agents.py               AgentNodes: tutor_node, evaluator_node, help-level escalation logic
  scenarios.py             SCENARIOS bank + ScenarioManager (per-student deterministic pick)
  auto_tester.py           compile-and-run grader + syntax-only checker (gcc/g++)
  helper.py                scoring formulas + LangGraph message-dedup helper
```

### `sessions.json`

One entry per student ID:
```json
{
  "<student_id>": {
    "student_id": "...",
    "completed_scenarios": ["bit_ops", "..."],
    "current": { "scenario_id", "scenario_name", "hint_count", "score",
                 "start_time", "last_active", "status" } ,
    "history": [ /* one completed-session record per finished scenario */ ]
  }
}
```
`current` is `null` when the student isn't mid-scenario. This file is plain
JSON read/written on every action — fine for a classroom-sized cohort, not
built for concurrent writers at scale.

### `Results/`

One log per completed session, named `session_{student_id}_{timestamp}.txt`,
containing the student ID, scenario, hint counts (with the level breakdown),
final score, and the full chat transcript. The teacher dashboard's **📋
לוגים** tab lists and opens these (filtered by the
`session_<id>_<date>_<time>.txt` naming pattern — see
`is_real_session_log()` in `app_shared.py`).

### `teacher_config.json`

Just `{ "teacher_password": "..." }` — the dashboard login password
(default `teacher123`, changeable from the dashboard's **⚙️ הגדרות** tab).
There is no per-student or global help-level setting anymore; help level is
fully automatic (see above).

---

## Teacher dashboard (`teacher_app.py`)

Password-gated (`teacher_config.json`'s `teacher_password`). Three tabs:

- **⚙️ הגדרות** — change the dashboard password, and a static reference table
  of scenario IDs.
- **👥 סטודנטים** — a table of every student who's logged in (scenarios
  completed, average/individual scores, current scenario, active/done
  status), a per-student view of completed scenario IDs, and their full
  session history (scenario, hints used, score, date).
- **📋 לוגים** — browse and open the raw `Results/*.txt` transcripts,
  filterable by student ID.

---

## Running it

**Prerequisites:**
- Python 3.10+ with the packages in `requirements.txt`:
  `pip install -r requirements.txt`
- [Ollama](https://ollama.com) installed and running locally, with the model
  pulled: `ollama pull qwen2.5-coder:7b` (the model name is hardcoded in
  `production_sim/graph.py`). Inference is CPU-bound unless your machine has
  a GPU Ollama can use — expect noticeably slower tutor replies on
  CPU-only hardware.
- `gcc` and `g++` on `PATH` (needed for the auto-grader).

**Run the student app:**
```bash
streamlit run student_app.py
```
or double-click `run_app.command` (macOS; it hardcodes an Anaconda Python
path — edit it if your `streamlit` lives elsewhere).

**Run the teacher dashboard** (on a different port, since both are Streamlit
apps and can't share one):
```bash
streamlit run teacher_app.py --server.port 8502
```

A `.env` file with `OPENAI_API_KEY` exists in the repo but **isn't read by
any code** — the tutor and evaluator both run entirely on the local Ollama
model. It's a leftover from an earlier design and safe to ignore (or
delete) unless you plan to wire in a hosted model later.

---

## Notable implementation details

- **LangGraph shape** (`production_sim/graph.py`): a single `router` node
  that dispatches on `state["current_phase"]` (`"chat"` → `tutor`,
  `"evaluation"` → `evaluator`), both terminal nodes ending the graph run.
  Message state uses a custom reducer (`add_unique_messages`) keyed by a
  UUID stamped on every `AIMessage`, so a node firing more than once in one
  `graph.stream()` pass can't duplicate a reply.
- **Two call paths for the tutor**: `run_graph()` (in `app_shared.py`) drives
  the LangGraph directly and is used for the very first greeting and for
  code evaluation; the interactive chat instead calls
  `AgentNodes.stream_tutor_response()` directly (bypassing the graph) so
  Streamlit can stream tokens — both paths share `_build_tutor_system()` and
  `compute_question_level()` so the behavior stays identical either way.
- **Dark mode** (`app_shared.py: render_dark_mode_toggle`) is a CSS override
  injected on top of Streamlit's own theme, since Streamlit has no runtime
  theme-switch API.
- **Anti-repeat scenario logic**: because `ScenarioManager` seeds off the
  student ID, restarting a session for the same student (without completing
  one) reproduces the same scenario — this is intentional, not a bug.
