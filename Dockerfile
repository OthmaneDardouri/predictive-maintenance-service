# syntax=docker/dockerfile:1

# ---- Build stage: install dependencies and the package into a virtualenv ----
FROM python:3.15.0-slim-trixie AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Dependencies first: this layer is reused until pyproject.toml changes.
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && pip install -r requirements.txt

COPY src ./src
RUN pip install --no-deps .

# ---- Runtime stage: only the virtualenv, the model and a non-root user ----
FROM python:3.15.0-slim-trixie AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    MODEL_PATH=/app/models/model.joblib

RUN useradd --create-home --uid 10001 app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY models/model.joblib models/metadata.json ./models/

USER app
EXPOSE 8000

# slim has no curl, so the healthcheck uses the Python standard library.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "pm_service.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
