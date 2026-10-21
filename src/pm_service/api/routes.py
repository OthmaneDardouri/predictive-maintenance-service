from fastapi import APIRouter, HTTPException, Request, status

from pm_service import __version__
from pm_service.api.schemas import HealthResponse, ModelInfo, VersionResponse

router = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}})
def ready(request: Request) -> HealthResponse:
    if request.app.state.model is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")
    return HealthResponse(status="ready")


@router.get("/version")
def version(request: Request) -> VersionResponse:
    model = request.app.state.model
    return VersionResponse(
        app_version=__version__,
        app_env=request.app.state.settings.app_env,
        model=ModelInfo.model_validate(model.metadata) if model else None,
    )
