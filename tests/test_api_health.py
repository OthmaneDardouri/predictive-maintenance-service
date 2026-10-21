from typing import Any

from fastapi.testclient import TestClient

from pm_service import __version__


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_model_loaded(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_not_ready_when_model_missing(client_without_model: TestClient) -> None:
    response = client_without_model.get("/ready")

    assert response.status_code == 503


def test_health_ok_even_when_model_missing(client_without_model: TestClient) -> None:
    # Liveness must not depend on the model, or Kubernetes would restart the pod in a loop.
    assert client_without_model.get("/health").status_code == 200


def test_version_returns_app_and_model_metadata(
    client: TestClient, model_metadata: dict[str, Any]
) -> None:
    body = client.get("/version").json()

    assert body["app_version"] == __version__
    assert body["app_env"] == "test"
    assert body["model"]["model_version"] == model_metadata["model_version"]
    assert body["model"]["features"] == model_metadata["features"]


def test_version_without_model(client_without_model: TestClient) -> None:
    body = client_without_model.get("/version").json()

    assert body["model"] is None
