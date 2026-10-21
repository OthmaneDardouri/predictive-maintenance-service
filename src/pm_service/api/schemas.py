from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ModelInfo(BaseModel):
    model_version: str
    sklearn_version: str
    trained_at: str
    features: list[str]
    metrics: dict[str, float]


class VersionResponse(BaseModel):
    app_version: str
    app_env: str
    model: ModelInfo | None
