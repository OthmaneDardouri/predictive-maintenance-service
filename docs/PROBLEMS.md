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

## Feature branches created from an outdated main
- **Problem:** twice I created the next phase branch before merging the previous pull
  request. `feat/docker` contained the Dockerfile but not the API code from phase 2, so
  the build would have failed.
- **How it was found:** the agent checked whether the previous branch was an ancestor of
  `HEAD` (`git merge-base --is-ancestor feat/api HEAD` → no).
- **Fix:** merged the phase 2 PR, then `git fetch origin` and
  `git rebase --autostash origin/main` on `feat/docker`. The branch was not pushed yet, so
  rewriting it was safe, and `--autostash` kept the uncommitted frontend work.
- **Lesson:** merge, `git pull`, and only then create the next branch.

## Docker Desktop could not start (WSL install stuck at 93.7%)
- **Problem:** `docker version` → `Docker Desktop is unable to start`; `wsl --install`
  seemed stuck at 93.7%.
- **Investigation:** `wsl --version` showed WSL 3.0.3 and its kernel already installed;
  `wsl -l -v` showed no distributions; the `wsl` process had an open connection to a
  Canonical server and its CPU time did not grow. So only the Ubuntu download was stuck.
- **Fix:** cancelled the Ubuntu download (Docker Desktop uses its own internal
  distribution), restarted Windows, started Docker Desktop.

## `npm` not recognized
- **Problem:** `npm install` → `The term 'npm' is not recognized`.
- **Cause:** Node.js was not installed. After installing it, an already-open terminal
  still did not see it: PATH changes only apply to new sessions.
- **Fix:** `winget install OpenJS.NodeJS.LTS`, then a new terminal.

## CI did not run on my "broken on purpose" commit
- **Problem:** I pushed a commit that breaks the quality gate, but no red check appeared.
- **Cause:** the commit was pushed after PR #5 had already been merged. The workflow runs
  only on `pull_request` and on `push` to `main`, so a push to a branch without an open
  PR triggers nothing.
- **Fix:** opened a new PR from a new branch with that commit.

## A PR with red CI was merged into main
- **Problem:** the CI on PR #6 failed as intended, but the PR was merged anyway, so `main`
  got `decision_threshold: 0.9` and the `v0.2.0` tag pointed at the broken commit.
- **Cause:** `main` had no branch protection, so GitHub allows merging regardless of the
  checks, even while they are still running.
- **What limited the damage:** the CI run on `main` failed, so the `publish` job (which
  needs e2e to pass) never ran. The `latest` image on GHCR stayed the good one.
- **Fix:** enabled branch protection on `main` (required status checks: the three CI jobs),
  reverted the commit with `git revert` in a PR (no history rewrite on a shared branch),
  and moved `v0.2.0` to the last green commit.
- **Lesson:** CI that reports failures is not enough; the repository must enforce them.
