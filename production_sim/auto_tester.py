"""
Compile-and-run auto-grader for student C/C++ functions.
Combines: part setup + student code + test harness → gcc/g++ → checks for ALL_PASS.
"""

import subprocess
import tempfile
import os
from typing import Tuple


def check_syntax(code: str, language: str = "c", setup: str = "") -> Tuple[bool, str]:
    """
    Fast syntax-only check (no linking, no execution) — lets a student catch
    typos/syntax mistakes before spending a full "Run Code" attempt on them.
    """
    blocks = [b.strip() for b in [setup, code] if b.strip()]
    combined = "\n\n".join(blocks)

    suffix = ".c" if language == "c" else ".cpp"
    compiler = "gcc" if language == "c" else "g++"
    extra_flags = [] if language == "c" else ["-std=c++17"]

    src_fd, src_path = tempfile.mkstemp(suffix=suffix)

    try:
        with os.fdopen(src_fd, "w", encoding="utf-8") as f:
            f.write(combined)

        proc = subprocess.run(
            [compiler, "-fsyntax-only", src_path, "-Wall", "-Wno-unused-variable"] + extra_flags,
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            return True, "✅ No syntax errors!"

        err = proc.stderr.strip().replace(src_path, "<student_code>")
        return False, f"**Syntax errors:**\n```\n{err}\n```"

    except subprocess.TimeoutExpired:
        return False, "⏱️ Syntax check took too long."
    except FileNotFoundError:
        return False, f"⚠️ `{compiler}` not found on the system. Make sure it's installed."
    except Exception as e:
        return False, f"⚠️ Error: {e}"
    finally:
        if os.path.exists(src_path):
            try:
                os.unlink(src_path)
            except OSError:
                pass


def auto_test(student_code: str, part: dict, timeout: int = 10) -> Tuple[bool, str]:
    """
    Returns (passed, feedback_markdown).
    part keys:
        setup (str, optional)    – preamble: typedefs, includes, reference helpers
        test_harness (str)       – test main() function
        language (str, optional) – "c" (default) or "cpp"
    Order in compiled file: setup → student_code → test_harness
    """
    language = part.get("language", "c")
    setup = part.get("setup", "")
    harness = part.get("test_harness", "")

    blocks = [b.strip() for b in [setup, student_code, harness] if b.strip()]
    combined = "\n\n".join(blocks)

    suffix = ".c" if language == "c" else ".cpp"
    compiler = "gcc" if language == "c" else "g++"
    extra_flags = ["-lm"] if language == "c" else ["-std=c++17", "-lm"]

    src_fd, src_path = tempfile.mkstemp(suffix=suffix)
    exe_path = src_path[: -len(suffix)]

    try:
        with os.fdopen(src_fd, "w", encoding="utf-8") as f:
            f.write(combined)

        compile_proc = subprocess.run(
            [compiler, src_path, "-o", exe_path, "-Wall", "-Wno-unused-variable"] + extra_flags,
            capture_output=True, text=True, timeout=30,
        )
        if compile_proc.returncode != 0:
            err = compile_proc.stderr.strip().replace(src_path, "<student_code>")
            return False, f"**Compilation error:**\n```\n{err}\n```"

        run_proc = subprocess.run(
            [exe_path], capture_output=True, text=True, timeout=timeout,
        )
        stdout = run_proc.stdout.strip()
        stderr = run_proc.stderr.strip()

        if "ALL_PASS" in stdout:
            return True, "✅ All tests passed successfully!"

        lines = []
        if stderr:
            lines.append(f"**Failed tests:**\n```\n{stderr}\n```")
        if stdout:
            lines.append(f"**Output:**\n```\n{stdout}\n```")
        if not lines:
            lines.append("Tests did not pass — try again.")
        return False, "\n".join(lines)

    except subprocess.TimeoutExpired:
        return False, "⏱️ **timeout** — the code did not finish running. Check for infinite loops."
    except FileNotFoundError:
        return False, f"⚠️ `{compiler}` not found on the system. Make sure it's installed."
    except Exception as e:
        return False, f"⚠️ Error: {e}"
    finally:
        for p in [src_path, exe_path]:
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass
