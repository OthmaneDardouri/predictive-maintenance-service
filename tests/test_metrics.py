from typing import Any

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

STRESSED_MACHINE: dict[str, Any] = {
    "type": "L",
    "air_temperature_k": 302.5,
    "process_temperature_k": 311.0,
    "rotational_speed_rpm": 1250,
    "torque_nm": 72.0,
    "tool_wear_min": 230,
}


def sample(name: str, labels: dict[str, str] | None = None) -> float:
    # Metrics live in a process-wide registry, so tests compare before/after values.
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def test_metrics_endpoint(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_request_is_counted_by_route_template(client: TestClient) -> None:
    labels = {"method": "GET", "path": "/health", "status": "200"}
    before = sample("http_requests_total", labels)

    client.get("/health")

    assert sample("http_requests_total", labels) == before + 1


def test_unknown_paths_share_one_label(client: TestClient) -> None:
    labels = {"method": "GET", "path": "unmatched", "status": "404"}
    before = sample("http_requests_total", labels)

    client.get("/random-1")
    client.get("/random-2")

    assert sample("http_requests_total", labels) == before + 2
    assert "/random-1" not in client.get("/metrics").text


def test_prediction_metrics(client: TestClient, auth_headers: dict[str, str]) -> None:
    before_predictions = sample("predictions_total", {"prediction": "1"})
    before_torque_sum = sample("model_input_torque_nm_sum")

    client.post("/predict", json=STRESSED_MACHINE, headers=auth_headers)

    assert sample("predictions_total", {"prediction": "1"}) == before_predictions + 1
    assert sample("model_input_torque_nm_sum") == before_torque_sum + 72.0


def test_rejected_request_is_not_a_prediction(client: TestClient) -> None:
    before = sample("prediction_failure_probability_count")

    assert client.post("/predict", json=STRESSED_MACHINE).status_code == 401
    assert sample("prediction_failure_probability_count") == before


def test_model_loaded_gauge(client: TestClient) -> None:
    assert sample("model_loaded") == 1


def test_model_loaded_gauge_without_model(client_without_model: TestClient) -> None:
    assert sample("model_loaded") == 0
