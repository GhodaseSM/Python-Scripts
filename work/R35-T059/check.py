import json
import platform
import random
import re
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path

from test_art2 import BASE_COLORS, expected_output, load_art_module


TASK_DIR = Path(__file__).resolve().parent
REPO_ROOT = TASK_DIR.parents[1]
SIZES = (32, 64, 102)
REPETITIONS = 5
SEED_START = 20261122


def run_native_tests():
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "work/R35-T059",
        "-p",
        "test_*.py",
        "-v",
    ]
    completed = subprocess.run(
        command, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    output = completed.stdout + completed.stderr
    match = re.search(r"Ran (\d+) tests?", output)
    test_count = int(match.group(1)) if match else 0
    log = {
        "command": shlex.join(command),
        "exit_code": completed.returncode,
        "tests_run": test_count,
        "output": output,
    }
    (TASK_DIR / "native-tests.json").write_text(
        json.dumps(log, indent=2) + "\n", encoding="utf-8"
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    if test_count == 0:
        raise AssertionError("Focused unittest command did not run any tests")
    return command, test_count


def run_measurements():
    records = []
    for size in SIZES:
        samples_ms = []
        size_runs = []
        for repetition in range(REPETITIONS):
            seed = SEED_START + (size * REPETITIONS) + repetition
            module = load_art_module()
            initial_colors = BASE_COLORS.copy()
            module.colors = initial_colors
            expected_colors, expected_circles, expected_final_colors = expected_output(
                seed, size
            )

            random.seed(seed)
            started = time.perf_counter_ns()
            result = module.main(size)
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
            samples_ms.append(elapsed_ms)

            actual_colors = [call.args[0] for call in module.color.call_args_list]
            actual_circles = [call.args for call in module.circle.call_args_list]
            actual_final_colors = module.colors.copy()
            actual = {
                "return": result,
                "selected_colors": actual_colors,
                "circles": actual_circles,
                "final_colors": actual_final_colors,
            }
            expected = {
                "return": None,
                "selected_colors": expected_colors,
                "circles": expected_circles,
                "final_colors": expected_final_colors,
            }
            if actual != expected:
                raise AssertionError(
                    f"Output mismatch for size={size}, repetition={repetition}: "
                    f"expected={expected!r}, actual={actual!r}"
                )
            if len(actual_circles) != size or len(actual_colors) != size:
                raise AssertionError(
                    f"Operation-count mismatch for size={size}: "
                    f"colors={len(actual_colors)}, circles={len(actual_circles)}"
                )

            size_runs.append(
                {
                    "repetition": repetition + 1,
                    "seed": seed,
                    "input": {"iterations": size, "initial_colors": BASE_COLORS},
                    "expected": expected,
                    "actual": actual,
                    "operation_counts": {
                        "shuffle_iterations": size,
                        "color_calls": len(actual_colors),
                        "circle_calls": len(actual_circles),
                    },
                    "elapsed_ms": elapsed_ms,
                }
            )

        records.append(
            {
                "iterations": size,
                "repetitions": REPETITIONS,
                "operation_counts_per_run": {
                    "shuffle_iterations": size,
                    "color_calls": size,
                    "circle_calls": size,
                },
                "elapsed_ms": {
                    "median": statistics.median(samples_ms),
                    "range": [min(samples_ms), max(samples_ms)],
                    "samples": samples_ms,
                },
                "runs": size_runs,
            }
        )
    return records


def main():
    test_command, test_count = run_native_tests()
    measurements = run_measurements()
    report = {
        "command_run": "python3 work/R35-T059/check.py",
        "python_process_argv": shlex.join(getattr(sys, "orig_argv", sys.argv)),
        "native_test_command": shlex.join(test_command),
        "native_test_exit_code": 0,
        "native_tests_run": test_count,
        "repository_test_configuration": "No pytest/pyproject/tox/setup.cfg configuration found; standard-library unittest used.",
        "target": "Turtle Art/art2.py",
        "cpu_only": True,
        "timing_note": "Turtle GUI is mocked; output assertions run after each timed call. Operation counts are the primary metric because the fixed drawing domain and tiny calls make wall-clock samples overhead-sensitive.",
        "tool_versions": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "unittest": "Python standard library",
        },
        "input_sizes": list(SIZES),
        "repetitions_per_size": REPETITIONS,
        "measurements": measurements,
    }
    (TASK_DIR / "results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    for item in measurements:
        timing = item["elapsed_ms"]
        print(
            f"iterations={item['iterations']}: "
            f"circle_calls={item['operation_counts_per_run']['circle_calls']}, "
            f"median={timing['median']:.6f} ms, "
            f"range=[{timing['range'][0]:.6f}, {timing['range'][1]:.6f}] ms"
        )
    print(f"Focused tests passed: {test_count}; evidence saved under {TASK_DIR}.")


if __name__ == "__main__":
    main()