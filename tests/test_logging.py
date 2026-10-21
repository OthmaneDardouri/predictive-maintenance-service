import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from pm_service.api.main import create_app
from pm_service.config import Settings

HEALTHY_MACHINE: dict[str, Any] = {
    "type": "M",
    "air_temperature_k": 298.1,
    "process_temperature_k": 308.6,
    "rotational_speed_rpm": 1551,
    "torque_nm": 42.8,
    "tool_wear_min": 0,
}


def read_json_logs(capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    lines = capsys.readouterr().out.splitlines()
    return [json.loads(line) for line in lines if line.startswith("{")]


def find_log(logs: list[dict[str, Any]], message: str) -> dict[str, Any]:
    return next(entry for entry in logs if entry["message"] == message)


def test_access_log_is_json_with_request_fields(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    response = client.get("/health")

    entry = find_log(read_json_logs(capsys), "request completed")
    assert entry["method"] == "GET"
    assert entry["path"] == "/health"
    assert entry["status"] == 200
    assert isinstance(entry["latency_ms"], float)
    assert entry["request_id"] == response.headers["X-Request-ID"]


def test_request_id_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health")

    assert len(response.headers["X-Request-ID"]) == 32


def test_valid_request_id_is_propagated(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"
    assert find_log(read_json_logs(capsys), "request completed")["request_id"] == "abc-123"


@pytest.mark.parametrize("bad_id", ["x" * 65, "has space", "line\nbreak"])
def test_invalid_request_id_is_replaced(client: TestClient, bad_id: str) -> None:
    response = client.get("/health", headers={"X-Request-ID": bad_id})

    assert response.headers["X-Request-ID"] != bad_id


def test_prediction_is_logged_without_api_key(
    client: TestClient, auth_headers: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    response = client.post("/predict", json=HEALTHY_MACHINE, headers=auth_headers)

    output = capsys.readouterr().out
    logs = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
    entry = find_log(logs, "prediction")
    assert entry["prediction"] == response.json()["prediction"]
    assert entry["model_version"] == response.json()["model_version"]
    assert entry["request_id"] == response.headers["X-Request-ID"]
    assert auth_headers["X-API-Key"] not in output


@pytest.fixture
def failing_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(Settings(_env_file=None, api_key="key", model_path=tmp_path / "none"))

    def boom() -> None:
        raise RuntimeError("secret internal detail")

    app.add_api_route("/boom", boom)
    with TestClient(app) as test_client:
        yield test_client


def test_unhandled_error_returns_generic_500(
    failing_client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    response = failing_client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}
    assert "secret internal detail" not in response.text
    error_log = find_log(read_json_logs(capsys), "unhandled error")
    assert error_log["level"] == "ERROR"
    assert "secret internal detail" in error_log["exception"]
