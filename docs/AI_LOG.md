# AI usage log

Log of prompts given to AI tools, what they proposed, what was wrong, and how it was verified.

Tool: Claude Code (VS Code extension). Workflow: the agent writes code in small steps and
stops after each one; I review the diff, run the checks, and commit myself
(rules in `AGENTS.md`).

## Phase 1 - Model

### 1. Breaking the phase into small steps
- **Prompt:** the phase 1 prompt from my plan (training pipeline, leakage rules, metrics).
- **Proposed:** the agent started doing everything at once (venv, dependency install,
  setup files).
- **What I changed:** I stopped it and asked for one step at a time, with unit tests and a
  commit after each step. It then proposed a 5-step plan (pyproject, preprocessing,
  tests, training, log) and waited for my "ok" between steps.
- **Lesson:** small steps make every diff reviewable and give a readable Git history.

### 2. Python version mismatch
- **Proposed:** `AGENTS.md` required Python 3.12, but only 3.15 was installed. The agent
  stopped and offered two options: install 3.12 or switch to 3.15.
- **Decision:** 3.15, and `AGENTS.md` was updated to match.
- **Verification:** `py -3.12 --version` failed, `python --version` returned 3.15.0.

### 3. Dependencies installed without asking
- **What was wrong:** the agent ran `pip install` without asking, even though `AGENTS.md`
  says to ask before installing dependencies. It reported this itself afterwards.
- **Lesson:** a rules file guides the agent but does not enforce anything. I still have
  to read what it runs.

### 4. Wrong diagnosis of a slow install
- **Proposed:** the install was slow, and the agent guessed that pip was compiling
  numpy/pandas from source because Python 3.15 has no wheels yet.
- **What was wrong:** the pip log showed `Connection interrupted while downloading` and
  a resume, so the network was the cause. The packages had wheels.
- **Verification:** read the actual command output instead of trusting the explanation.

### 5. CSV byte-order mark (BOM)
- **Proposed:** the agent saw a BOM before `UDI` in the CSV header and suspected it would
  corrupt the first column name.
- **Verification:** before adding `encoding="utf-8-sig"`, it checked with pandas, and the
  column name was already clean. False alarm, no code added.
- **Lesson:** verify a suspicion before adding "just in case" code.

### 6. Data leakage
- **Rule given:** TWF, HDF, PWF, OSF, RNF are failure-mode flags set together with the
  target, so they must not be features. UDI and Product ID must be excluded too.
- **Proposed:** a whitelist of features (`FEATURES`) instead of dropping columns, plus a
  test asserting that leakage and ID columns are never in `X`.
- **Verification:**
  - test-set metrics are realistic (recall 0.66, PR-AUC 0.76). With leakage they would
    be close to 1.0.
  - broke `split_features_target` on purpose (`df.drop(columns=[TARGET])`) and checked
    that the test fails.

### 7. Versioning the model artifact
- **Proposed:** two options for the 7.5 MB `model.joblib`: (A) commit it to Git,
  (B) ignore it and train in CI.
- **Decision:** A, because it is simple and CI/Docker can use the model directly.
  Downside: every retrain adds 7.5 MB to the repo history. A model registry would fix
  this (see production gaps).

## Phase 2 - API

### 8. Dependencies: asked first this time
- **Proposed:** fastapi, uvicorn, pydantic-settings, httpx with versions checked via
  `pip index versions` (read-only), then waited for my approval before installing.
- **Surprise:** fastapi 0.156 pulled in `opentelemetry-api`, which older versions did not.

### 9. Deprecation warning corrected the AI's knowledge
- **Proposed:** `httpx` for FastAPI's `TestClient` (the standard setup the agent knew).
- **What happened:** running the tests with `-W error` showed that starlette 1.9
  deprecates `httpx` in favour of `httpx2`. The agent did not know this.
- **Decision:** kept `httpx` for now (works, one warning). To revisit before it breaks.
- **Lesson:** run tests with warnings visible; recent library changes are where the AI's
  knowledge is weakest.

### 10. Lint caught a non-idiomatic pattern
- **Proposed:** FastAPI dependencies as default values (`model = Depends(get_model)`).
- **What was wrong:** ruff `B008` flagged it. The agent rewrote them with `Annotated`,
  which is the style recommended by current FastAPI docs.
- **Lesson:** lint AI-generated code like any other code.

### 11. Wrong first hypothesis on failing logging tests
- **Proposed:** 4 logging tests failed; the agent first blamed pytest fixture order.
- **Verification:** a temporary test with both fixture orders failed too, so the
  hypothesis was wrong. Printing the root logger handlers showed the real cause (see
  `PROBLEMS.md`).
- **Lesson:** test a hypothesis before applying a fix based on it.

### 12. Manual end-to-end check
- **Verification:** besides the 36 unit/API tests, started a real uvicorn server and
  sent requests: `/ready` 200, `/predict` 200 with probability 0.95 for a stressed
  machine, 401 without key, 422 with negative torque. Logs were JSON with the same
  `request_id` on the prediction log and the access log.
