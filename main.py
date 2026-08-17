"""
Coding Tutor Simulator - CLI Orchestrator
=========================================

Two modes:
  Teacher mode  (--teacher):  set the help level saved to teacher_config.json
  Student mode  (default):    chat with the tutor, then submit code for grading

Help levels
-----------
  1  Strict    – guiding questions only, no answers
  2  Guided    – conceptual hints, no code
  3  Supported – full explanations with code examples
"""

import os
import sys
import json
import argparse
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from production_sim import CodingTutorSim

CONFIG_FILE = "teacher_config.json"


# --------------------------------------------------
# LOGGER
# --------------------------------------------------
class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def log_only(self, message):
        if self.log and not self.log.closed:
            self.log.write(message + "\n")

    def flush(self):
        self.terminal.flush()
        if self.log and not self.log.closed:
            self.log.flush()


# --------------------------------------------------
# CONFIG HELPERS
# --------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"help_level": 2}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# --------------------------------------------------
# TEACHER MODE
# --------------------------------------------------
def teacher_mode():
    current = load_config()
    print("\n=== TEACHER MODE ===")
    print(f"Current help level: {current.get('help_level', 2)}\n")
    print("  1 – Strict    (guiding questions only)")
    print("  2 – Guided    (conceptual hints, no code)")
    print("  3 – Supported (full explanations + code examples)\n")

    raw = input("Enter new help level (1 / 2 / 3): ").strip()
    if raw in ("1", "2", "3"):
        save_config({"help_level": int(raw)})
        labels = {1: "Strict", 2: "Guided", 3: "Supported"}
        print(f"\n✅ Help level set to {raw} – {labels[int(raw)]}")
    else:
        print("❌ Invalid input. No changes saved.")


# --------------------------------------------------
# INPUT HELPERS
# --------------------------------------------------
def get_multiline_input(prompt_header):
    print(f"\n{prompt_header}")
    print("   (Type 'DONE' on a new line and press Enter to submit)")
    print("   " + "-" * 50)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "DONE":
            break
        lines.append(line)
    return "\n".join(lines)


# --------------------------------------------------
# GRAPH RUNNER
# --------------------------------------------------
already_printed_ids = set()


def run_graph(app, state):
    global already_printed_ids
    latest_state = state

    for node_state in app.stream(state):
        for _, node_dict in node_state.items():
            filtered = [
                msg for msg in node_dict.get("messages", [])
                if type(msg).__name__ in ("AIMessage", "SystemMessage")
            ]
            for msg in filtered:
                msg_id = (
                    getattr(msg, "id", None)
                    or msg.additional_kwargs.get("id")
                    or hash(msg.content)
                )
                if msg_id and msg_id not in already_printed_ids:
                    print(f"\nTutor: {msg.content}\n")
                    already_printed_ids.add(msg_id)

            latest_state = node_dict

    return latest_state


# --------------------------------------------------
# STUDENT MODE
# --------------------------------------------------
def student_mode(help_level: int):
    results_dir = "Results"
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(results_dir, f"session_{timestamp}.txt")
    sys.stdout = Logger(log_filename)

    level_labels = {1: "Strict", 2: "Guided", 3: "Supported"}
    print("--- Coding Tutor Simulator ---")
    print(f"Help level: {help_level} – {level_labels.get(help_level, '?')}")
    print(f"Session log: {log_filename}\n")

    student_id = input("Enter your Student ID: ").strip() or "default_user"

    sim = CodingTutorSim(student_id=student_id, help_level=help_level)
    app = sim.compile()
    state = sim.get_initial_state()

    # Present the task
    state = run_graph(app, state)

    while True:
        user_input = get_multiline_input("📝 Your message (or start with SUBMIT to submit your code):")

        if isinstance(sys.stdout, Logger):
            sys.stdout.log_only(f"\n--- Student input @ {datetime.now().strftime('%H:%M:%S')} ---\n{user_input}\n" + "-" * 40)

        if not user_input.strip():
            print("(empty input, try again)")
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Session ended.")
            break

        # Detect SUBMIT
        first_line = user_input.strip().splitlines()[0].strip().upper()
        if first_line == "SUBMIT":
            # Code is everything after the first line
            code = "\n".join(user_input.strip().splitlines()[1:]).strip()
            if not code:
                code = get_multiline_input("📋 Paste your code below:")

            state["submitted_code"] = code
            state["current_phase"] = "evaluation"
            state["messages"] = state.get("messages", []) + [HumanMessage(content=code)]
        else:
            state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]

        state = run_graph(app, state)

        if state.get("current_phase") == "done":
            score = state.get("score", 0)
            hints = state.get("hint_count", 0)
            print("\n" + "=" * 50)
            print("Session complete!")
            print(f"Final score : {score}/100")
            print(f"Hints used  : {hints}")
            print("=" * 50)
            if isinstance(sys.stdout, Logger):
                sys.stdout.log.close()
            break


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Coding Tutor Simulator")
    parser.add_argument("--teacher", action="store_true", help="Open teacher configuration mode")
    args = parser.parse_args()

    if args.teacher:
        teacher_mode()
        return

    config = load_config()
    help_level = config.get("help_level", 2)
    student_mode(help_level)


if __name__ == "__main__":
    main()
