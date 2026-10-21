import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pm_service import __version__
from pm_service.api.routes import router
from pm_service.config import Settings, get_settings
from pm_service.model import load_model

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved = settings or get_settings()
        app.state.settings = resolved
        app.state.model = None
        try:
            app.state.model = load_model(resolved.model_path)
            logger.info("Model %s loaded from %s", app.state.model.version, resolved.model_path)
        except Exception:
            # Stay alive but not ready: /health passes, /ready returns 503.
            logger.exception("Failed to load model from %s", resolved.model_path)
        yield

    app = FastAPI(title="Predictive Maintenance Service", version=__version__, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
