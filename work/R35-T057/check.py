#!/usr/bin/env python3
"""Run focused Canny checks and preserve their inputs, results, and versions."""

import importlib.metadata
import json
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = Path(__file__).resolve().parent
TARGET = "Road-Lane-Detection/dik2_1.py"
NATIVE_COMMAND = [
    sys.executable,
    "-m",
    "unittest",
    "discover",
    "-s",
    "work/R35-T057",
    "-p",
    "test_*.py",
    "-v",
]
RUNNER_COMMAND = f"{shlex.quote(sys.executable)} work/R35-T057/check.py"


def write_json(filename, value):
    (WORK_DIR / filename).write_text(
        json.dumps(value, indent=2) + "\n", encoding="utf-8"
    )


def git_output(*args):
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def record_inputs():
    write_json("inputs.json", {
        "reviewed_before_change": {
            "base_commit": git_output("rev-parse", "--short", "HEAD"),
            "source_blob": git_output("rev-parse", f"HEAD:{TARGET}"),
            "public_function": "canny_edge_detection(frame)",
            "input": "One OpenCV-compatible BGR image; no explicit validation or defaults.",
            "result": "The array returned by cv2.Canny, normally a single-channel uint8 edge image with the frame's height and width.",
            "mutation": "Does not assign into or otherwise intentionally mutate frame; conversion, blur, and Canny create intermediate/result arrays.",
            "dependencies": {
                "function_direct": ["cv2.cvtColor", "cv2.GaussianBlur", "cv2.Canny"],
                "module_imports": ["cv2", "numpy (used by other functions in the module)"],
                "video_demo_io": "cv2.VideoCapture/imshow/waitKey/release/destroyAllWindows; moved under main() and mocked by the focused check.",
            },
        },
        "test_fixture": {
            "input": "5x5 image where every BGR pixel is [0, 255, 0]",
            "expected_grayscale_pixel": 150,
            "expected_blur": "5x5 matrix of 150 (uniform input)",
            "expected_canny_edges": "5x5 matrix of 0 (uniform input has no gradients)",
            "method": "Hand-calculate each intermediate state, inject those states at the cv2 boundary, then compare against function locals captured by sys.settrace.",
            "scope_limit": "cv2 and numpy are stubbed because they are not installed in the selected workspace environment; this verifies API wiring and mutation/return behavior, not OpenCV's native algorithms.",
        },
        "test_framework": "Python standard-library unittest; the repository has no pytest.ini, pyproject.toml, tox.ini, or setup.cfg test configuration.",
        "external_io": "Video capture and display calls are mocked; no video file, camera, or GUI is opened.",
    })


def record_tool_versions():
    package_versions = {}
    for package in ("opencv-python", "numpy"):
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = "not installed; mocked in focused checks"

    write_json("tool_versions.json", {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "git_version": git_output("--version"),
        "test_framework": "unittest (Python standard library)",
        "packages": package_versions,
    })


def main():
    record_inputs()
    record_tool_versions()

    actual_command = shlex.join(NATIVE_COMMAND)
    print(f"Runner command: {RUNNER_COMMAND}", flush=True)
    print("Requested invocation: python3 work/R35-T057/check.py", flush=True)
    print(f"Native focused test command: {actual_command}", flush=True)
    result = subprocess.run(
        NATIVE_COMMAND,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout, end="")

    match = re.search(r"^Ran (\d+) tests? in ", result.stdout, re.MULTILINE)
    test_count = int(match.group(1)) if match else 0
    trace_path = WORK_DIR / "trace_execution.json"
    traced_results = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else None
    write_json("results.json", {
        "runner_command": RUNNER_COMMAND,
        "requested_invocation": "python3 work/R35-T057/check.py",
        "native_test_command": actual_command,
        "native_test_count": test_count,
        "exit_code": result.returncode,
        "status": "PASS" if result.returncode == 0 and test_count > 0 else "FAIL",
        "stdout_and_stderr": result.stdout,
        "hand_expected_vs_traced_actual": traced_results,
    })

    if test_count == 0:
        print("Focused test command did not execute any tests.", file=sys.stderr)
        return result.returncode or 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
