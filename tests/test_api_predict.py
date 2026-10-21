from typing import Any

import pytest
from fastapi.testclient import TestClient

HEALTHY_MACHINE: dict[str, Any] = {
    "type": "M",
    "air_temperature_k": 298.1,
    "process_temperature_k": 308.6,
    "rotational_speed_rpm": 1551,
    "torque_nm": 42.8,
    "tool_wear_min": 0,
}

# High torque at low speed with a worn tool: a typical overstrain failure.
STRESSED_MACHINE: dict[str, Any] = {
    "type": "L",
    "air_temperature_k": 302.5,
    "process_temperature_k": 311.0,
    "rotational_speed_rpm": 1250,
    "torque_nm": 72.0,
    "tool_wear_min": 230,
}


def test_predict_healthy_machine(
    client: TestClient, auth_headers: dict[str, str], model_metadata: dict[str, Any]
) -> None:
    response = client.post("/predict", json=HEALTHY_MACHINE, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["failure_probability"] <= 1.0
    assert body["prediction"] == 0
    assert body["model_version"] == model_metadata["model_version"]


def test_predict_stressed_machine(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/predict", json=STRESSED_MACHINE, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["prediction"] == 1


def test_predict_without_api_key(client: TestClient) -> None:
    response = client.post("/predict", json=HEALTHY_MACHINE)

    assert response.status_code == 401


def test_predict_with_wrong_api_key(client: TestClient) -> None:
    response = client.post("/predict", json=HEALTHY_MACHINE, headers={"X-API-Key": "wrong"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "override",
    [
        {"type": "X"},
        {"torque_nm": -5},
        {"rotational_speed_rpm": 0},
        {"air_temperature_k": 1000},
        {"tool_wear_min": "a lot"},
        {"unexpected_field": 1},
    ],
)
def test_predict_rejects_invalid_input(
    client: TestClient, auth_headers: dict[str, str], override: dict[str, Any]
) -> None:
    response = client.post("/predict", json=HEALTHY_MACHINE | override, headers=auth_headers)

    assert response.status_code == 422


def test_predict_rejects_missing_field(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {k: v for k, v in HEALTHY_MACHINE.items() if k != "torque_nm"}

    response = client.post("/predict", json=payload, headers=auth_headers)

    assert response.status_code == 422


def test_predict_without_model_returns_503(
    client_without_model: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client_without_model.post("/predict", json=HEALTHY_MACHINE, headers=auth_headers)

    assert response.status_code == 503
