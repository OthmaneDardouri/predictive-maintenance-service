import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _api_key() -> str:
    if key := os.environ.get("API_KEY"):
        return key
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("API_KEY="):
            return line.removeprefix("API_KEY=").strip()
    raise RuntimeError("API_KEY not set and not found in .env")


@pytest.fixture(scope="session")
def api_key() -> str:
    return _api_key()


@pytest.fixture(scope="session")
def api() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=os.environ.get("E2E_API_URL", "http://localhost:8000")) as client:
        yield client


@pytest.fixture(scope="session")
def frontend() -> Iterator[httpx.Client]:
    url = os.environ.get("E2E_FRONTEND_URL", "http://localhost:8080")
    with httpx.Client(base_url=url) as client:
        yield client
