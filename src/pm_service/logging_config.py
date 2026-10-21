import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RESERVED_ATTRS: set[str] = set(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "color_message",
}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Anything passed via `extra=` becomes a top-level JSON field.
        payload.update({k: v for k, v in vars(record).items() if k not in _RESERVED_ATTRS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class JsonStdoutHandler(logging.StreamHandler):
    def __init__(self) -> None:
        super().__init__(sys.stdout)
        self.setFormatter(JsonFormatter())
        self.addFilter(RequestIdFilter())

    def emit(self, record: logging.LogRecord) -> None:
        # Resolve stdout on each write: binding it once breaks when stdout is redirected
        # (e.g. pytest capture), leaving the handler writing to a closed stream.
        self.stream = sys.stdout
        super().emit(record)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    # Replace only our own handler, so repeated calls (and pytest's handlers) are left alone.
    root.handlers = [h for h in root.handlers if not isinstance(h, JsonStdoutHandler)]
    root.addHandler(JsonStdoutHandler())
    root.setLevel(level)

    # Route uvicorn's own logs through our JSON handler; our middleware writes the access log.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
