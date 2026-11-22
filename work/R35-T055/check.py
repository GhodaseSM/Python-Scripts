#!/usr/bin/env python3
"""Run focused, isolated checks for Video Downloader/VideoDownloader.py."""

import json
import os
import platform
import re
import shlex
import subprocess
import sys

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(WORK_DIR, "..", ".."))
INPUTS_PATH = os.path.join(WORK_DIR, "inputs.json")
OBSERVATIONS_PATH = os.path.join(WORK_DIR, "observations.json")
RESULTS_PATH = os.path.join(WORK_DIR, "expected_vs_actual.json")
VERSIONS_PATH = os.path.join(WORK_DIR, "tool_versions.json")


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def record_tool_versions():
    git_version = "unknown"
    try:
        result = subprocess.run(
            ["git", "--version"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        git_version = result.stdout.strip() or result.stderr.strip()
    except OSError as error:
        git_version = str(error)

    versions = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "git_version": git_version,
        "test_framework": "unittest (Python standard library; project convention)",
    }
    save_json(VERSIONS_PATH, versions)
    return versions


def run_native_tests():
    """Use the repository's unittest discovery convention for only this target's tests."""
    test_dir = os.path.join("Video Downloader", "tests")
    command = [sys.executable, "-m", "unittest", "discover", "-s", test_dir, "-p", "test_*.py"]
    command_text = shlex.join(command)
    print(f"[RUNNER] Native test command: {command_text}", flush=True)

    if os.path.exists(OBSERVATIONS_PATH):
        os.remove(OBSERVATIONS_PATH)

    environment = os.environ.copy()
    environment["R35_T055_OBSERVATIONS_PATH"] = OBSERVATIONS_PATH
    result = subprocess.run(
        command, cwd=REPO_ROOT, env=environment, capture_output=True, text=True, check=False
    )
    output = result.stdout + result.stderr
    print(output, end="" if output.endswith("\n") else "\n", flush=True)
    count_match = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+", output)
    test_count = int(count_match.group(1)) if count_match else 0

    if result.returncode != 0:
        raise RuntimeError(
            f"Focused unittest command failed (exit {result.returncode}); command={command_text}\n{output}"
        )
    if test_count <= 0:
        raise RuntimeError(f"Focused unittest command ran no tests; command={command_text}\n{output}")
    if not os.path.exists(OBSERVATIONS_PATH):
        raise RuntimeError("The repeatability test did not save its actual observations.")

    with open(OBSERVATIONS_PATH, encoding="utf-8") as file:
        observations = json.load(file)
    return command_text, test_count, output, observations


def main():
    print("[RUNNER] Starting focused Video Downloader checks.", flush=True)
    with open(INPUTS_PATH, encoding="utf-8") as file:
        inputs = json.load(file)
    versions = record_tool_versions()

    expected = inputs["test_fixture"]
    expected_fixture = expected["expected_download_result"]
    expected_other = expected["other_expected_download_result"]
    native_command = "not run"
    test_count = 0
    test_output = ""
    observations = {}

    try:
        native_command, test_count, test_output, observations = run_native_tests()
        fixture_runs = observations["same_fixture_fresh_isolated_runs"]
        sequence = observations["after_another_valid_input"]
        assert fixture_runs == [expected_fixture, expected_fixture], (
            f"Fresh-state fixture results differ: {fixture_runs!r}"
        )
        assert sequence["before_other_input"] == expected_fixture
        assert sequence["other_valid_input_result"] == expected_other
        assert sequence["fixture_after_other_input"] == expected_fixture
        assert sequence["before_other_input"] == sequence["fixture_after_other_input"], (
            "The intervening valid input changed the later fixture result."
        )

        results = {
            "status": "PASSED",
            "target_module_only": "Video Downloader/VideoDownloader.py",
            "runner_command": "python3 work/R35-T055/check.py",
            "native_test_command": native_command,
            "nonzero_test_count": test_count,
            "external_io_policy": "pytube/YouTube, input, and the target download are mocked; the runner writes JSON evidence files locally.",
            "expected_vs_actual": {
                "same_fixture_fresh_isolated_runs": {
                    "expected": [expected_fixture, expected_fixture],
                    "actual": fixture_runs,
                    "match": True,
                },
                "fixture_after_another_valid_input": {
                    "expected": expected_fixture,
                    "actual": sequence["fixture_after_other_input"],
                    "match": True,
                    "intervening_input": expected["other_valid_url"],
                    "intervening_expected_actual": {
                        "expected": expected_other,
                        "actual": sequence["other_valid_input_result"],
                    },
                },
            },
            "unittest_output": test_output,
            "tool_versions": versions,
        }
        save_json(RESULTS_PATH, results)
        print(f"[RUNNER] PASS: {test_count} focused tests; artifacts saved under {WORK_DIR}.")
        return 0
    except Exception as error:
        save_json(RESULTS_PATH, {
            "status": "FAILED",
            "runner_command": "python3 work/R35-T055/check.py",
            "native_test_command": native_command,
            "nonzero_test_count": test_count,
            "expected": expected,
            "actual_observations": observations,
            "unittest_output": test_output,
            "error": str(error),
            "tool_versions": versions,
        })
        print(f"[RUNNER] FAIL: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
