from pathlib import Path

import pytest
from pydantic import ValidationError

from pm_service.config import Settings

ENV_VARS: list[str] = ["APP_ENV", "LOG_LEVEL", "MODEL_PATH", "API_KEY"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("MODEL_PATH", "/opt/models/model.joblib")
    monkeypatch.setenv("API_KEY", "secret-from-env")

    settings = Settings(_env_file=None)

    assert settings.app_env == "prod"
    assert settings.log_level == "WARNING"
    assert settings.model_path == Path("/opt/models/model.joblib")
    assert settings.api_key.get_secret_value() == "secret-from-env"


def test_defaults_when_only_api_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "secret-from-env")

    settings = Settings(_env_file=None)

    assert settings.app_env == "dev"
    assert settings.log_level == "INFO"
    assert settings.model_path == Path("models/model.joblib")


def test_missing_api_key_fails() -> None:
    with pytest.raises(ValidationError, match="api_key"):
        Settings(_env_file=None)


def test_invalid_app_env_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "secret-from-env")
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValidationError, match="app_env"):
        Settings(_env_file=None)


def test_api_key_is_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "secret-from-env")

    settings = Settings(_env_file=None)

    assert "secret-from-env" not in repr(settings)
    assert "secret-from-env" not in str(settings.model_dump())
