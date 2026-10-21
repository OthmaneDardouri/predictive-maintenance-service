# Problems log

Real blockers hit during the project, what was tried, and how (or whether) they were resolved.

## Python 3.12 not available locally
- **Problem:** the project rules required Python 3.12, but `py -3.12` failed with
  `No runtime installed that matches 3.12`. Only Python 3.15 was installed.
- **Options:** install 3.12 with `py install 3.12`, or use 3.15.
- **Resolution:** used 3.15 and updated `AGENTS.md`. All dependencies (pandas 3.0.6,
  scikit-learn 1.9.1) installed from wheels.
- **Open point:** the Docker base image (phase 3) must use the same Python version as
  local development, or behaviour may differ between environments.

## JSON logs missing in tests (closed stream)
- **Problem:** 4 logging tests failed with `StopIteration`: no JSON log line was found in
  the captured stdout, although the app clearly logged (pytest showed the records).
- **First hypothesis (wrong):** pytest fixture order, i.e. the handler created before
  `capsys` replaced stdout. A temporary test with both orders failed the same way.
- **Investigation:** printed the root logger handlers during a test and saw
  `ValueError: I/O operation on closed file`.
- **Cause:** `logging.StreamHandler(sys.stdout)` binds the stream once at creation.
  pytest swaps `sys.stdout` for every test, so the handler kept writing to an old,
  closed capture stream.
- **Fix:** the handler resolves `sys.stdout` at each `emit()`. Production behaviour is
  unchanged (stdout is never swapped there), and tests now read the real JSON output.
