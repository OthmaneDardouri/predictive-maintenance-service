import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from pm_service.api.main import create_app
from pm_service.config import Settings

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "model.joblib"
TEST_API_KEY = "test-api-key"


def make_settings(model_path: Path) -> Settings:
    return Settings(_env_file=None, app_env="test", api_key=TEST_API_KEY, model_path=model_path)


@pytest.fixture
def model_metadata() -> dict[str, Any]:
    return json.loads((MODEL_PATH.parent / "metadata.json").read_text())


@pytest.fixture
def client() -> Iterator[TestClient]:
    # The with-block runs the lifespan, so the model is loaded.
    with TestClient(create_app(make_settings(MODEL_PATH))) as test_client:
        yield test_client


@pytest.fixture
def client_without_model(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(tmp_path / "missing.joblib"))) as test_client:
        yield test_client
