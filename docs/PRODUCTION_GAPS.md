# Production gaps

An honest list of what is **not** production-ready, and what I would do about it.

## Model and data

- **No model registry.** The model is a 7.5 MB file in Git; every retrain grows the repo
  history. Use a registry (MLflow, S3 with versioning) and reference a model version in
  config.
- **No retraining pipeline.** Training is a manual script; the holdout must be re-exported
  by hand. A scheduled or triggered pipeline should train, evaluate against the gate and
  the current model, and register the result.
- **Untuned decision threshold.** 0.5 gives recall 0.66: one failure in three is missed.
  The threshold should be chosen with the business cost of a missed failure vs. a false
  alarm (e.g. from the precision-recall curve).
- **No ground-truth feedback.** Real model quality is unknown in production. Predictions
  should be joined with maintenance records to track recall over time.
- **Drift monitoring is minimal**: one feature, mean only. Track all features with a
  proper statistic (e.g. PSI).
- **`joblib` is pickle**: loading a tampered file runs arbitrary code. The model must come
  from a trusted, access-controlled location (signed artifact or registry).
- **No dataset versioning** (e.g. DVC): the training data is not tracked.

## Security

- **One static API key**, shared by nginx and the API, no rotation, no per-client
  identity. Options: keys per client with rotation, or OAuth2/OIDC.
- **The frontend is open**: anyone who reaches it can make predictions. A real deployment
  needs user login in front of it.
- **No HTTPS.** TLS should terminate at an Ingress or load balancer.
- **No rate limiting** on `/predict`.
- **Secrets in Kubernetes are base64, not encrypted** by default. Use a secret manager
  (AWS Secrets Manager, Vault) with External Secrets Operator, and encryption at rest.
- **No image scanning or SBOM** in CI (e.g. Trivy), and actions are pinned by tag, not
  by commit SHA.

## Operations

- **Build once, deploy many is not respected**: CI builds the image for e2e, then the
  publish job builds it again. The published image is not byte-for-byte the tested one.
- **App version is never bumped**: `0.1.0` in `pyproject.toml` and `__init__.py` (two
  places) while tags are at `v0.2.0`. Use one source of truth (e.g. version from the tag).
- **Docker compose exposes the API port (8000)** on the host, so the API and `/metrics`
  are reachable bypassing nginx. Fine locally; in production only the entry point should
  be exposed.
- **Kubernetes**: no NetworkPolicy (any pod can call the API and `/metrics`), no
  PodDisruptionBudget, the frontend has a single replica, no Ingress. With the HPA,
  `replicas: 2` in the Deployment is reset by every `kubectl apply`.
- **No load test**: resource requests/limits and the HPA threshold are guesses.
- **API image is ~700 MB** (scipy, pandas, sklearn). Slower pulls and scaling.
- **No alerting stack**: alerts are documented in `MONITORING.md` but no Prometheus,
  Alertmanager or dashboard is deployed. No log aggregation either.
- **Single uvicorn worker per container**; scaling is horizontal (more pods). Multiple
  workers would need `prometheus-client` multiprocess mode.

## Deployment to the cloud (not done)

How it would go, e.g. on AWS:
1. CI pushes the image to a registry (GHCR already works, or ECR).
2. A managed Kubernetes cluster (EKS) runs the same manifests, with the image referenced
   by its commit SHA tag.
3. The API key lives in a secret manager and reaches the pods through workload identity
   (IRSA / EKS Pod Identity), not static credentials.
4. An Ingress with a managed load balancer and TLS certificate exposes only the frontend.
5. Deploys go through CI (or GitOps, e.g. Argo CD) instead of manual `kubectl apply`.

## Testing

- The `TestClient` uses `httpx`, which starlette 1.9 deprecates in favour of `httpx2`
  (warning in every test run).
- e2e tests check one happy path per feature; no tests for concurrency, timeouts or a
  restarting API behind nginx.
