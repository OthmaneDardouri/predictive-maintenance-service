"""End-to-end tests against the running docker compose stack (see scripts/run_e2e.py)."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.e2e

METADATA_PATH = Path(__file__).resolve().parents[2] / "models" / "metadata.json"

STRESSED_MACHINE: dict[str, Any] = {
    "type": "L",
    "air_temperature_k": 302.5,
    "process_temperature_k": 311.0,
    "rotational_speed_rpm": 1250,
    "torque_nm": 72.0,
    "tool_wear_min": 230,
}


def test_api_is_live_and_ready(api: httpx.Client) -> None:
    assert api.get("/health").status_code == 200
    assert api.get("/ready").status_code == 200


def test_api_serves_committed_model_version(api: httpx.Client) -> None:
    expected = json.loads(METADATA_PATH.read_text())["model_version"]

    assert api.get("/version").json()["model"]["model_version"] == expected


def test_api_predict_requires_key(api: httpx.Client, api_key: str) -> None:
    assert api.post("/predict", json=STRESSED_MACHINE).status_code == 401

    response = api.post("/predict", json=STRESSED_MACHINE, headers={"X-API-Key": api_key})

    assert response.status_code == 200
    assert response.json()["prediction"] == 1


def test_frontend_serves_console(frontend: httpx.Client) -> None:
    response = frontend.get("/")

    assert response.status_code == 200
    assert "Machine Health Console" in response.text


def test_proxy_predicts_without_client_key(frontend: httpx.Client) -> None:
    response = frontend.post("/api/predict", json=STRESSED_MACHINE)

    assert response.status_code == 200
    assert response.json()["prediction"] == 1


def test_proxy_replaces_client_supplied_key(frontend: httpx.Client) -> None:
    # nginx overwrites the header, so a browser cannot pick which key is used.
    response = frontend.post(
        "/api/predict", json=STRESSED_MACHINE, headers={"X-API-Key": "attacker-guess"}
    )

    assert response.status_code == 200


def test_proxy_passes_validation_errors_through(frontend: httpx.Client) -> None:
    response = frontend.post("/api/predict", json=STRESSED_MACHINE | {"torque_nm": -5})

    assert response.status_code == 422


def test_proxy_propagates_request_id(frontend: httpx.Client) -> None:
    response = frontend.get("/api/health")

    assert len(response.headers["X-Request-ID"]) == 32


def test_api_exposes_metrics_internally(api: httpx.Client) -> None:
    response = api.get("/metrics")

    assert response.status_code == 200
    assert "predictions_total" in response.text


def test_proxy_does_not_expose_metrics(frontend: httpx.Client) -> None:
    assert frontend.get("/api/metrics").status_code == 404


def test_frontend_bundle_does_not_contain_key(frontend: httpx.Client, api_key: str) -> None:
    html = frontend.get("/").text
    scripts = [part.split('"')[0] for part in html.split('src="')[1:]]

    assert api_key not in html
    for path in scripts:
        assert api_key not in frontend.get(path).text
