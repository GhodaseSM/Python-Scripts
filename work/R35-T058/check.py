#!/usr/bin/env python3
"""Run focused PDF-to-Audio regression tests and save reproducible evidence."""

import json
import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path


WORK_DIR = Path(__file__).resolve().parent
REPO_ROOT = WORK_DIR.parents[1]
TEST_FILE = WORK_DIR / "test_audio_book.py"


def save_json(filename, value):
    path = WORK_DIR / filename
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def record_tool_versions():
    git_version = "unknown"
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=False
        )
        git_version = result.stdout.strip() or result.stderr.strip()
    except OSError as error:
        git_version = f"unavailable: {error}"

    versions = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "git_version": git_version,
        "test_framework": "unittest (Python standard library)",
        "external_test_dependencies": "Mocked; no third-party package required by the runner",
    }
    save_json("tool_versions.json", versions)
    return versions


def run_native_tests():
    """Use focused unittest discovery; the test imports no other project module."""
    relative_test_dir = os.path.relpath(WORK_DIR, REPO_ROOT)
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        relative_test_dir,
        "-p",
        TEST_FILE.name,
        "-v",
    ]
    display_command = shlex.join(command)
    print(f"[CHECK] Native test command: {display_command}")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    print(output, end="" if output.endswith("\n") else "\n")
    (WORK_DIR / "native_test_output.txt").write_text(
        f"Command: {display_command}\nExit code: {result.returncode}\n\n{output}",
        encoding="utf-8",
    )

    count_match = re.search(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE)
    test_count = int(count_match.group(1)) if count_match else 0
    return display_command, result.returncode, test_count, output


def main():
    record_tool_versions()
    command, exit_code, test_count, output = run_native_tests()
    expected_vs_actual = {
        "requested_runner_invocation": "python3 work/R35-T058/check.py",
        "project_test_configuration": "No repository pytest/unittest config was present; use the focused standard-library unittest discovery command below.",
        "baseline_observation_before_source_change": {
            "input": "empty string ('')",
            "source_branch": "int(val) raises ValueError before PDF parsing or speech starts",
            "baseline_resource_order": "The original module opened python_basics.pdf before converting the input.",
            "expected": "ValueError; malformed input must not open or mutate caller-owned PDF state; a valid retry must work.",
            "baseline_test_command": "\"/Users/sharwarighodase/Desktop/S an AI Projects/Python-Scripts/.venv/bin/python\" -m unittest discover -s work/R35-T058 -p test_audio_book.py -v",
            "baseline_exit_code": 1,
            "baseline_test_count": 2,
            "baseline_actual": "One regression test failed: the malformed input raised ValueError, but the mocked PDF open had already been called once. The valid-input test passed.",
        },
        "post_change_checks": {
            "native_test_command": command,
            "native_test_exit_code": exit_code,
            "nonzero_test_count": test_count,
            "test_suite_status": "ALL_TESTS_PASSED" if exit_code == 0 and test_count > 0 else "FAILED",
            "expected": [
                "Empty input raises ValueError before opening the PDF or initializing speech.",
                "Caller-owned input and PDF bytes remain valid after failure.",
                "A successful invocation works after the failure with mocked PDF/speech I/O.",
                "Valid input uses only the mocked PDF reader and speech engine.",
            ],
            "actual_output": output,
        },
    }
    save_json("expected_vs_actual.json", expected_vs_actual)

    if exit_code != 0:
        print(f"[CHECK] Focused Python tests failed (exit code {exit_code}).", file=sys.stderr)
        return exit_code
    if test_count <= 0:
        print("[CHECK] unittest reported no tests; failing closed.", file=sys.stderr)
        return 1

    print(f"[CHECK] Passed {test_count} focused tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
