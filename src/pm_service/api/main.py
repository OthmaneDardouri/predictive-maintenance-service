import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pm_service import __version__
from pm_service.api.middleware import request_context_middleware
from pm_service.api.routes import router
from pm_service.config import Settings, get_settings
from pm_service.logging_config import configure_logging
from pm_service.metrics import MODEL_LOADED
from pm_service.model import load_model

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved = settings or get_settings()
        configure_logging(resolved.log_level)
        app.state.settings = resolved
        app.state.model = None
        MODEL_LOADED.set(0)
        try:
            model = load_model(resolved.model_path)
            app.state.model = model
            MODEL_LOADED.set(1)
            logger.info("Model %s loaded from %s", model.version, resolved.model_path)
        except Exception:
            # Stay alive but not ready: /health passes, /ready returns 503.
            logger.exception("Failed to load model from %s", resolved.model_path)
        yield

    app = FastAPI(title="Predictive Maintenance Service", version=__version__, lifespan=lifespan)
    app.middleware("http")(request_context_middleware)
    app.include_router(router)
    return app


app = create_app()
