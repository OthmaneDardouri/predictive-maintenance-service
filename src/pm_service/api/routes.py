from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from pm_service import __version__
from pm_service.api.schemas import (
    HealthResponse,
    ModelInfo,
    PredictRequest,
    PredictResponse,
    VersionResponse,
)
from pm_service.api.security import require_api_key
from pm_service.model import LoadedModel

router = APIRouter()


def get_model(request: Request) -> LoadedModel:
    model: LoadedModel | None = request.app.state.model
    if model is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")
    return model


ModelDep = Annotated[LoadedModel, Depends(get_model)]


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}})
def ready(model: ModelDep) -> HealthResponse:
    return HealthResponse(status="ready")


@router.get("/version")
def version(request: Request) -> VersionResponse:
    model = request.app.state.model
    return VersionResponse(
        app_version=__version__,
        app_env=request.app.state.settings.app_env,
        model=ModelInfo.model_validate(model.metadata) if model else None,
    )


@router.post("/predict", dependencies=[Depends(require_api_key)])
def predict(payload: PredictRequest, model: ModelDep) -> PredictResponse:
    probability = model.predict_failure_probability(payload.model_dump())
    return PredictResponse(
        failure_probability=probability,
        prediction=1 if probability >= model.threshold else 0,
        model_version=model.version,
    )
