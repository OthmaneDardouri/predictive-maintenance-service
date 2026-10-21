from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class PredictRequest(BaseModel):
    # Bounds are physically plausible limits, wider than the training data range.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "type": "M",
                    "air_temperature_k": 298.1,
                    "process_temperature_k": 308.6,
                    "rotational_speed_rpm": 1551,
                    "torque_nm": 42.8,
                    "tool_wear_min": 0,
                }
            ]
        },
    )

    type: Literal["L", "M", "H"]
    air_temperature_k: float = Field(ge=250, le=350)
    process_temperature_k: float = Field(ge=250, le=400)
    rotational_speed_rpm: float = Field(gt=0, le=5000)
    torque_nm: float = Field(ge=0, le=200)
    tool_wear_min: float = Field(ge=0, le=500)


class PredictResponse(BaseModel):
    failure_probability: float
    prediction: Literal[0, 1]
    model_version: str
