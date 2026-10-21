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
