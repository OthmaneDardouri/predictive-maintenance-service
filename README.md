# predictive-maintenance-service

Machine failure prediction service based on the
[AI4I 2020 Predictive Maintenance](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset)
dataset: a scikit-learn model served by a FastAPI API.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

python scripts/train.py          # needs data/raw/ai4i2020.csv
pytest
ruff check .

$env:API_KEY="dev-key"; uvicorn pm_service.api.main:app --reload
```

API docs: http://localhost:8000/docs

## Tests

| Command | What it runs |
|---|---|
| `pytest` | unit and API tests, plus the model quality gate (e2e excluded) |
| `python scripts/run_e2e.py` | starts docker compose, waits for `/ready`, runs the e2e tests, stops the stack |

The quality gate (`tests/test_model_quality.py`) fails if recall on the failure class
drops below 0.60 or PR-AUC below 0.70 on the holdout set in `tests/data/holdout.csv`.
After retraining, regenerate the holdout with `python scripts/export_holdout.py`.

## CI

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every pull
request and on every push to `main`:

```text
python (ruff + pytest) ──┐
                         ├──> e2e (docker compose + run_e2e.py) ──> publish (main only)
frontend (tsc + build) ──┘
```

On `main`, the API image is pushed to GitHub Container Registry as
`ghcr.io/<owner>/pm-service-api:<commit sha>` and `:latest`, using the built-in
`GITHUB_TOKEN` with `packages: write` only for that job.

## Docker

Create `.env` from the template and set a real `API_KEY`:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Test it:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: <your API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"type":"L","air_temperature_k":302.5,"process_temperature_k":311.0,"rotational_speed_rpm":1250,"torque_nm":72.0,"tool_wear_min":230}'
```

## Frontend

The Machine Health Console (Vite + TypeScript, no framework) is served by nginx at
http://localhost:8080 when running `docker compose up`.

The browser calls `/api/predict` on the same origin. nginx forwards it to the API and adds
`X-API-Key` server-side, so the key never reaches the browser.

```text
browser ──/api/predict──> nginx (frontend, :8080) ──/predict + X-API-Key──> api (:8000)
```

Local development with hot reload (needs the API running on port 8000):

```powershell
cd frontend
npm install
$env:API_KEY="<your API_KEY>"; npm run dev    # http://localhost:5173
```

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | liveness: the process is running |
| GET | `/ready` | no | readiness: the model is loaded (503 otherwise) |
| GET | `/version` | no | app version and model metadata |
| POST | `/predict` | `X-API-Key` | failure probability for one machine |
