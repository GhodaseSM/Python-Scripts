# Baseline behavior audit: `Turtle Art/art2.py`

Recorded from the source before edits.

- **Public entry point:** `main()` takes no arguments. There are no documented preconditions or return-value contracts.
- **Inputs:** the function reads module-global `colors` (`['sky blue', 'navy', 'steel blue', 'cyan']`) and consumes the process-global `random` generator state. The loop's domain is fixed: `range(0, 204, 2)`, exactly 102 iterations.
- **Result:** returns `None` implicitly. Each iteration calls `color(colors[0])`, then `circle(10 + i, 100, 2)`, with `i` increasing from 0 to 202 by 2. Thus the radii are 10, 12, ..., 212.
- **Mutation/side effects:** `random.shuffle(colors)` mutates the shared module-level list in place once per iteration. Turtle drawing state is also changed by `color`/`circle`; import itself calls `speed(-1)` and `width(3)`. Executing the script directly additionally calls `ht()`, then `main()` twice, then `mainloop()`.
- **Dependencies:** Python standard-library `random` and `turtle`. `turtle` is GUI/Tk-backed and unsuitable for headless/CPU-only checks, so tests will replace its drawing API before importing this module. No network, filesystem, or other external I/O is part of `main()`.
- **Repository test configuration:** no root `pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`, or `conftest.py` was found. Existing repository tests include `unittest`; focused checks will use the standard-library `unittest` runner and import only this target module with Turtle mocked.
