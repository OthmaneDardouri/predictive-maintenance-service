import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from pm_service import __version__, metrics
from pm_service.api.schemas import (
    HealthResponse,
    ModelInfo,
    PredictRequest,
    PredictResponse,
    VersionResponse,
)
from pm_service.api.security import require_api_key
from pm_service.model import LoadedModel

logger = logging.getLogger(__name__)
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
    response = PredictResponse(
        failure_probability=probability,
        prediction=1 if probability >= model.threshold else 0,
        model_version=model.version,
    )
    logger.info("prediction", extra=response.model_dump())

    metrics.PREDICTIONS.labels(str(response.prediction)).inc()
    metrics.FAILURE_PROBABILITY.observe(probability)
    metrics.INPUT_TORQUE.observe(payload.torque_nm)
    return response


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
