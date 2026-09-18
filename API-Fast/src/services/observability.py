"""Observability: request id, JSON logs, health, metrics."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import Counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..config.settings import settings

_metrics = Counter()
_latency_ms = 0.0
_latency_n = 0


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _latency_ms, _latency_n
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        _latency_ms += elapsed
        _latency_n += 1
        _metrics[f"http_{response.status_code}"] += 1
        response.headers["X-Request-Id"] = request_id
        return response


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    level = getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if settings.LOG_JSON else logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def render_metrics() -> str:
    lines = [
        "# HELP dpu_http_requests_total HTTP responses",
        "# TYPE dpu_http_requests_total counter",
    ]
    for key, value in _metrics.items():
        lines.append(f'dpu_http_requests_total{{code="{key}"}} {value}')
    avg = (_latency_ms / _latency_n) if _latency_n else 0
    lines.append("# HELP dpu_http_latency_ms_avg Average request latency")
    lines.append("# TYPE dpu_http_latency_ms_avg gauge")
    lines.append(f"dpu_http_latency_ms_avg {avg:.2f}")
    return "\n".join(lines) + "\n"
