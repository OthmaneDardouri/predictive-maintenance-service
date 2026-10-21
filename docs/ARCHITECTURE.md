# Architecture

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Training | scikit-learn, `scripts/train.py` | trains a RandomForest pipeline, writes `model.joblib` + `metadata.json` |
| Model package | `src/pm_service/` | shared preprocessing (feature list, column names), model loading, prediction |
| API | FastAPI, uvicorn | validation, auth, prediction, health/readiness, logs, metrics |
| Frontend | Vite + TypeScript, nginx | static console; nginx proxies `/api` and adds the API key |
| Packaging | Docker multi-stage, docker compose | one image per component, non-root |
| CI | GitHub Actions | lint, tests, quality gate, e2e, image publish |
| Orchestration | Kubernetes (kind) | replicas, probes, config/secret injection, autoscaling |

## Flow of a prediction request

1. The browser posts the form to `/api/predict` on the same origin (no CORS, no key).
2. **nginx** matches `location /api/`, strips the prefix, sets `X-API-Key` from its
   environment (overwriting anything the client sent), sets `X-Request-ID` to its own
   `$request_id`, and forwards to `api:8000/predict`.
3. **Middleware** (`api/middleware.py`) keeps the request id if valid (otherwise
   generates one), stores it in a `ContextVar` so every log line of this request carries
   it, and starts a timer.
4. **Auth** (`api/security.py`) compares the header with `API_KEY` in constant time → 401.
5. **Validation**: FastAPI parses the body into `PredictRequest` (types, ranges, allowed
   `type` values, no extra fields) → 422 with field-level details.
6. **Readiness**: the `get_model` dependency returns the model loaded at startup → 503 if
   there is none.
7. **Prediction** (`model.py`): builds a one-row DataFrame in the training column order,
   runs the full pipeline (one-hot + RandomForest), applies the threshold from metadata.
8. The route logs the prediction and updates the prediction metrics.
9. Back in the middleware: request count and latency metrics, access log line, the
   `X-Request-ID` response header. Unhandled exceptions become a generic 500; the stack
   trace goes to the logs only.

## Design choices and alternatives

| Choice | Why | Alternative considered |
|---|---|---|
| Preprocessing inside the sklearn `Pipeline` | training and serving cannot diverge | separate transform code in the API |
| Feature **whitelist** (`FEATURES`) | leakage columns (TWF, HDF, ...) can never slip in | dropping known bad columns |
| Metrics on the failure class (recall, PR-AUC) | 3.4% failures: accuracy is meaningless | accuracy |
| Model committed to Git and baked into the image | simple; image version = model version | download from a model registry at startup |
| Model loaded once in `lifespan` | no per-request cost; readiness reflects it | lazy load on first request |
| App stays alive if the model fails to load | Kubernetes stops traffic (readiness) without restart loops | crash on startup |
| Settings from env vars, `API_KEY` required, `SecretStr` | no secret in code or images, fails fast, not logged | config file, default key |
| nginx adds the key server-side | key never reaches the browser | real user login (much more work) |
| `prometheus-client` with own middleware | full control, one small dependency | auto-instrumentation library |
| Route template as metric label | bounded cardinality | raw URL path |
| Holdout set versioned in `tests/data/` | quality gate runs in CI without the dataset | full dataset in the repo, or gate only locally |
| kind + `port-forward` | closest to real Kubernetes on a laptop | minikube; Ingress controller |
