# Monitoring

The API exposes Prometheus metrics at `GET /metrics` (port 8000). The endpoint is meant
for Prometheus on the internal network: the nginx frontend returns 404 for `/api/metrics`.

## Metrics

| Metric | Type | What it answers |
|---|---|---|
| `http_requests_total{method, path, status}` | counter | traffic and error rate per endpoint |
| `http_request_duration_seconds{method, path}` | histogram | latency (p50, p95, p99) |
| `model_loaded` | gauge | is a model loaded (same as readiness) |
| `predictions_total{prediction}` | counter | how many failures vs. OK are predicted |
| `prediction_failure_probability` | histogram | how confident the model is |
| `model_input_torque_nm` | histogram | is the input distribution drifting |

`path` is the route template (`/predict`), never the raw URL: unknown paths are all
labelled `unmatched`, so random URLs cannot create unbounded label values.

## What I would alert on in production

| Alert | PromQL (sketch) | Why |
|---|---|---|
| API down | `up{job="pm-service-api"} == 0` for 1m | nothing works |
| Model not loaded | `model_loaded == 0` for 2m | pods alive but not serving |
| Error rate > 5% | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05` | bugs or dependency failures |
| p95 latency > 500 ms | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{path="/predict"}[5m]))) > 0.5` | users or upstream systems wait |
| Predicted failure share > 15% | `sum(rate(predictions_total{prediction="1"}[1h])) / sum(rate(predictions_total[1h])) > 0.15` | training base rate is 3.4%: the machines or the inputs changed |
| Torque drift | mean torque `rate(model_input_torque_nm_sum[1h]) / rate(model_input_torque_nm_count[1h])` outside 30-50 Nm | training mean is 40 Nm (std 10): the model may no longer be valid |

Logs (JSON on stdout, with `request_id`) complement the metrics: metrics tell that
something is wrong, logs tell which request and why.

## Not covered yet

- **Real model quality.** Ground truth (did the machine actually fail?) arrives later. A
  production system would join predictions with maintenance records and track recall
  over time; input drift is only an early proxy.
- **Drift on all features**, with a proper statistic (e.g. PSI) instead of a mean.
- **Multiple workers.** `prometheus-client` keeps metrics per process; with several
  uvicorn workers it needs multiprocess mode. In Kubernetes, one worker per pod avoids it.
- **Prometheus, Grafana and Alertmanager** are not part of this repo.
