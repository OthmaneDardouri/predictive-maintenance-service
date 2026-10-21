"""Start the docker compose stack, wait until it is ready, run the e2e tests, tear it down."""

import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
READY_URL = "http://localhost:8080/api/ready"
READY_TIMEOUT_S = 120


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def create_env_file() -> None:
    # CI has no .env: create one from the template with a throwaway random key.
    template = (ROOT / ".env.example").read_text()
    key = secrets.token_urlsafe(32)
    ENV_FILE.write_text(template.replace("API_KEY=change-me", f"API_KEY={key}"))


def wait_until_ready() -> None:
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            if httpx.get(READY_URL, timeout=2).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(2)
    raise TimeoutError(f"{READY_URL} not ready after {READY_TIMEOUT_S}s")


def main() -> int:
    created_env = not ENV_FILE.exists()
    if created_env:
        create_env_file()
    try:
        compose("up", "-d", "--build")
        wait_until_ready()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-m", "e2e", "tests/e2e", "-v"],
            cwd=ROOT,
            env=os.environ.copy(),
        )
        if result.returncode != 0:
            compose("logs", "--no-color", "--tail", "50")
        return result.returncode
    finally:
        compose("down")
        if created_env:
            ENV_FILE.unlink()


if __name__ == "__main__":
    sys.exit(main())
