import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from pm_service.logging_config import request_id_var
from pm_service.metrics import HTTP_LATENCY, HTTP_REQUESTS

logger = logging.getLogger("pm_service.access")

REQUEST_ID_HEADER = "X-Request-ID"
# The header comes from the client: accept only short, safe values before logging it.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _resolve_request_id(request: Request) -> str:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    return incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex


def _route_template(request: Request) -> str:
    # Label by route template, never the raw URL: random 404 paths would create
    # unbounded label values (high cardinality) in Prometheus.
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = _resolve_request_id(request)
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error")
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "internal server error"},
            )
        elapsed = time.perf_counter() - start
        route = _route_template(request)
        HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
        HTTP_LATENCY.labels(request.method, route).observe(elapsed)

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(elapsed * 1000, 2),
            },
        )
        return response
    finally:
        request_id_var.reset(token)
