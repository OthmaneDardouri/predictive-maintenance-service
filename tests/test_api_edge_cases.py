import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from pm_service.api.main import create_app
from pm_service.config import Settings

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "model.joblib"

BASE: dict[str, Any] = {
    "type": "M",
    "air_temperature_k": 298.1,
    "process_temperature_k": 308.6,
    "rotational_speed_rpm": 1551,
    "torque_nm": 42.8,
    "tool_wear_min": 0,
}


@pytest.mark.parametrize(
    "override",
    [
        {"air_temperature_k": 250},
        {"air_temperature_k": 350},
        {"process_temperature_k": 400},
        {"rotational_speed_rpm": 5000},
        {"torque_nm": 0},
        {"tool_wear_min": 500},
    ],
)
def test_predict_accepts_boundary_values(
    client: TestClient, auth_headers: dict[str, str], override: dict[str, Any]
) -> None:
    response = client.post("/predict", json=BASE | override, headers=auth_headers)

    assert response.status_code == 200


def test_prediction_is_consistent_with_threshold(
    client: TestClient, auth_headers: dict[str, str], model_metadata: dict[str, Any]
) -> None:
    body = client.post("/predict", json=BASE, headers=auth_headers).json()

    expected = int(body["failure_probability"] >= model_metadata["decision_threshold"])
    assert body["prediction"] == expected


def test_predict_with_empty_api_key(client: TestClient) -> None:
    response = client.post("/predict", json=BASE, headers={"X-API-Key": ""})

    assert response.status_code == 401


def test_predict_with_malformed_json(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/predict",
        content="{not json",
        headers=auth_headers | {"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_predict_wrong_method(client: TestClient) -> None:
    assert client.get("/predict").status_code == 405


def test_error_responses_carry_request_id(client: TestClient) -> None:
    response = client.post("/predict", json=BASE)

    assert response.status_code == 401
    assert "X-Request-ID" in response.headers


@pytest.fixture
def client_without_metadata(tmp_path: Path) -> Iterator[TestClient]:
    shutil.copy(MODEL_PATH, tmp_path / "model.joblib")
    settings = Settings(_env_file=None, api_key="key", model_path=tmp_path / "model.joblib")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_not_ready_when_metadata_missing(client_without_metadata: TestClient) -> None:
    # A model without its metadata has no version or threshold: serving it would be unsafe.
    assert client_without_metadata.get("/ready").status_code == 503
