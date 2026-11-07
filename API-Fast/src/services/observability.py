"""Observability for the API and the background worker.

* Prometheus metrics on ``prometheus_client`` (HTTP by route/status, face GPU queue, face match,
  kiosk WebSockets, notification outbox, import jobs, background jobs, DB pool, readiness).
* W3C ``traceparent`` / ``X-Request-Id`` / company-id request context for log correlation.
* Structured JSON logs with PII redaction.
* Optional OpenTelemetry tracing (FastAPI + SQLAlchemy + httpx) exported over OTLP. Tracing is a
  no-op unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` (or ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``) is set.

The legacy helpers (``observe_histogram``, ``set_gauge``, ``inc_gauge``, ``render_metrics``,
``get_observability_summary``) are kept so existing callers and the admin UI summary keep working.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple
import uuid

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily

from ..config.settings import settings

logger = logging.getLogger("dpu.observability")

# --------------------------------------------------------------------------------------
# Request / job context
# --------------------------------------------------------------------------------------
current_request_id_var: ContextVar[str] = ContextVar("dpu_request_id", default="")
current_trace_id_var: ContextVar[str] = ContextVar("dpu_trace_id", default="")
current_span_id_var: ContextVar[str] = ContextVar("dpu_span_id", default="")
current_company_id_var: ContextVar[str] = ContextVar("dpu_company_id", default="")
current_job_var: ContextVar[str] = ContextVar("dpu_job", default="")

SERVICE_ROLE = os.environ.get("DPU_SERVICE_ROLE", "api")


def set_service_role(role: str) -> None:
    """``api`` or ``worker``; shows up in logs and ``dpu_build_info``."""
    global SERVICE_ROLE
    SERVICE_ROLE = role
    _build_info.info({"version": _APP_VERSION, "role": role})


def set_company_context(company_id: Any) -> Any:
    """Bind the tenant for log correlation. Returns the token for ``reset_company_context``."""
    return current_company_id_var.set(str(company_id) if company_id else "")


def reset_company_context(token: Any) -> None:
    try:
        current_company_id_var.reset(token)
    except Exception:
        pass


# --------------------------------------------------------------------------------------
# Prometheus metrics
# --------------------------------------------------------------------------------------
_APP_VERSION = os.environ.get("DPU_APP_VERSION", "4.0.0")
_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_LONG_BUCKETS = (0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)

_build_info = Info("dpu_build", "Build / role information of this process")
_build_info.info({"version": _APP_VERSION, "role": SERVICE_ROLE})

http_requests_total = Counter(
    "dpu_http_requests_total",
    "HTTP requests by method, route template and status code",
    ["method", "route", "status"],
)
http_request_duration_seconds = Histogram(
    "dpu_http_request_duration_seconds",
    "HTTP request latency by method and route template",
    ["method", "route"],
    buckets=_LATENCY_BUCKETS,
)
http_requests_in_progress = Gauge(
    "dpu_http_requests_in_progress", "HTTP requests currently being handled", ["method"]
)

face_gpu_queue_wait_seconds = Histogram(
    "dpu_face_gpu_queue_wait_seconds",
    "Time a face job waited in the GPU queue before a worker picked it up",
    ["kind"],
    buckets=_LATENCY_BUCKETS,
)
face_gpu_processing_seconds = Histogram(
    "dpu_face_gpu_processing_seconds",
    "InsightFace inference time per job kind",
    ["kind"],
    buckets=_LATENCY_BUCKETS,
)
face_gpu_jobs_total = Counter(
    "dpu_face_gpu_jobs_total", "Face GPU jobs by kind and result", ["kind", "result"]
)
face_match_duration_seconds = Histogram(
    "dpu_face_match_duration_seconds",
    "1:N face match latency (pgvector HNSW search or Face Core call)",
    ["source"],
    buckets=_LATENCY_BUCKETS,
)
ws_kiosk_connections = Gauge(
    "dpu_ws_kiosk_connections", "Open kiosk WebSocket connections on this process"
)

outbox_pending = Gauge(
    "dpu_outbox_pending", "Notification outbox rows waiting for delivery"
)
outbox_oldest_pending_age_seconds = Gauge(
    "dpu_outbox_oldest_pending_age_seconds",
    "Age of the oldest pending outbox row (dispatcher lag)",
)
outbox_claims_total = Counter(
    "dpu_outbox_claims_total", "Outbox rows claimed with FOR UPDATE SKIP LOCKED"
)
outbox_deliveries_total = Counter(
    "dpu_outbox_deliveries_total",
    "Outbox delivery attempts by channel and result (sent|retry|failed|skipped)",
    ["channel", "result"],
)
outbox_delivery_duration_seconds = Histogram(
    "dpu_outbox_delivery_duration_seconds",
    "Outbox delivery call latency by channel",
    ["channel"],
    buckets=_LATENCY_BUCKETS,
)

job_runs_total = Counter(
    "dpu_job_runs_total", "Background job runs by job name and result (ok|error)", ["job_name", "result"]
)
job_duration_seconds = Histogram(
    "dpu_job_duration_seconds", "Background job run duration", ["job_name"], buckets=_LONG_BUCKETS
)
job_last_run_timestamp_seconds = Gauge(
    "dpu_job_last_run_timestamp_seconds", "Unix time of the last run of a background job", ["job_name"]
)
job_last_success_timestamp_seconds = Gauge(
    "dpu_job_last_success_timestamp_seconds",
    "Unix time of the last successful run of a background job",
    ["job_name"],
)
job_in_progress = Gauge("dpu_job_in_progress", "Background job currently running", ["job_name"])

import_jobs_pending = Gauge("dpu_import_jobs_pending", "Employee import jobs waiting for a worker")
import_jobs_running = Gauge("dpu_import_jobs_running", "Employee import jobs currently processing")
import_jobs_total = Counter(
    "dpu_import_jobs_total", "Employee import jobs finished by result (done|failed)", ["result"]
)
import_job_duration_seconds = Histogram(
    "dpu_import_job_duration_seconds", "Employee import job processing time", buckets=_LONG_BUCKETS
)
import_job_rows_total = Counter(
    "dpu_import_job_rows_total", "Employee import rows by result (success|failed)", ["result"]
)

ready_status = Gauge(
    "dpu_ready_status", "Readiness probe component status (1 = ok, 0 = failing)", ["component"]
)


def set_ready_status(component: str, ok: bool) -> None:
    ready_status.labels(component=component).set(1.0 if ok else 0.0)


def observe_face_gpu_job(
    kind: str, *, wait_seconds: float, processing_seconds: float, result: str = "ok"
) -> None:
    k = kind or "other"
    face_gpu_queue_wait_seconds.labels(kind=k).observe(max(0.0, wait_seconds))
    face_gpu_processing_seconds.labels(kind=k).observe(max(0.0, processing_seconds))
    face_gpu_jobs_total.labels(kind=k, result=result).inc()


def observe_face_match(source: str, seconds: float) -> None:
    face_match_duration_seconds.labels(source=source or "pgvector").observe(max(0.0, seconds))


def set_outbox_backlog(pending: int, oldest_created_at: Optional[datetime]) -> None:
    outbox_pending.set(float(pending))
    if oldest_created_at is None or pending <= 0:
        outbox_oldest_pending_age_seconds.set(0.0)
        return
    created = oldest_created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    outbox_oldest_pending_age_seconds.set(
        max(0.0, (datetime.now(timezone.utc) - created).total_seconds())
    )


@contextmanager
def track_job(job: str) -> Iterator[None]:
    """Record duration / result / last-success for one background job run."""
    job_in_progress.labels(job_name=job).inc()
    job_last_run_timestamp_seconds.labels(job_name=job).set(time.time())
    tok = current_job_var.set(job)
    t0 = time.perf_counter()
    ok = False
    try:
        yield
        ok = True
    finally:
        job_duration_seconds.labels(job_name=job).observe(time.perf_counter() - t0)
        job_runs_total.labels(job_name=job, result="ok" if ok else "error").inc()
        if ok:
            job_last_success_timestamp_seconds.labels(job_name=job).set(time.time())
        job_in_progress.labels(job_name=job).dec()
        current_job_var.reset(tok)


class _LiveCollector:
    """Face GPU queue + SQLAlchemy pool gauges read at scrape time (no background sampling)."""

    def collect(self):
        yield from self._queue_metrics()
        yield from self._pool_metrics()

    @staticmethod
    def _queue_metrics():
        try:
            from ..utils.face_gpu_queue import face_gpu_queue_stats

            q = face_gpu_queue_stats()
        except Exception:
            return
        pending = GaugeMetricFamily(
            "dpu_face_gpu_queue_pending", "Face jobs waiting in the GPU queue by kind", labels=["kind"]
        )
        for kind, n in (q.get("pendingByKind") or {}).items():
            pending.add_metric([str(kind)], float(n or 0))
        yield pending
        g = GaugeMetricFamily("dpu_face_gpu_queue_pending_total", "Face jobs waiting in the GPU queue")
        g.add_metric([], float(q.get("pending") or 0))
        yield g
        g = GaugeMetricFamily("dpu_face_gpu_queue_active_jobs", "Face jobs currently on a GPU worker")
        g.add_metric([], float(q.get("active") or 0))
        yield g
        g = GaugeMetricFamily("dpu_face_gpu_queue_workers", "Configured face GPU worker tasks")
        g.add_metric([], float(q.get("workers") or 0))
        yield g
        g = GaugeMetricFamily("dpu_face_gpu_queue_capacity", "Soft backpressure limit of the GPU queue")
        g.add_metric([], float(q.get("maxsize") or 0))
        yield g
        g = GaugeMetricFamily("dpu_face_gpu_queue_started", "1 when the GPU queue workers are running")
        g.add_metric([], 1.0 if q.get("started") else 0.0)
        yield g

    @staticmethod
    def _pool_metrics():
        try:
            from ..config.database import engine

            pool = engine.pool
        except Exception:
            return
        values = {}
        for name, attr in (
            ("size", "size"),
            ("checked_in", "checkedin"),
            ("checked_out", "checkedout"),
            ("overflow", "overflow"),
        ):
            fn = getattr(pool, attr, None)
            if fn is None:
                continue
            try:
                values[name] = float(fn())
            except Exception:
                continue
        for name, val in values.items():
            g = GaugeMetricFamily(f"dpu_db_pool_{name}", f"SQLAlchemy connection pool {name}")
            g.add_metric([], val)
            yield g


_live_collector = _LiveCollector()
try:
    REGISTRY.register(_live_collector)
except ValueError:  # already registered (module reload)
    pass

# Legacy, name-addressed metrics ------------------------------------------------------
_lock = threading.Lock()
_legacy_histograms: Dict[str, Histogram] = {}
_legacy_gauges: Dict[str, Gauge] = {}
_LEGACY_HIST_ALIASES = {
    "dpu_face_gpu_latency_ms": lambda ms: face_gpu_processing_seconds.labels(kind="other").observe(
        ms / 1000.0
    ),
    "dpu_pgvector_search_ms": lambda ms: face_match_duration_seconds.labels(
        source="pgvector"
    ).observe(ms / 1000.0),
    "dpu_http_request_duration_ms": lambda ms: http_request_duration_seconds.labels(
        method="ANY", route="legacy"
    ).observe(ms / 1000.0),
}
_LEGACY_GAUGE_ALIASES = {"dpu_ws_active_kiosks": ws_kiosk_connections}


def observe_histogram(name: str, value_ms: float) -> None:
    """Legacy entry point (milliseconds). Known names map onto the typed metrics above."""
    val = max(0.0, float(value_ms))
    alias = _LEGACY_HIST_ALIASES.get(name)
    if alias is not None:
        alias(val)
        return
    with _lock:
        hist = _legacy_histograms.get(name)
        if hist is None:
            metric_name = re.sub(r"_ms$", "", name) + "_seconds"
            hist = Histogram(metric_name, f"Legacy histogram {name}", buckets=_LATENCY_BUCKETS)
            _legacy_histograms[name] = hist
    hist.observe(val / 1000.0)


def _legacy_gauge(name: str) -> Gauge:
    alias = _LEGACY_GAUGE_ALIASES.get(name)
    if alias is not None:
        return alias
    with _lock:
        g = _legacy_gauges.get(name)
        if g is None:
            g = Gauge(name, f"Legacy gauge {name}")
            _legacy_gauges[name] = g
        return g


def set_gauge(name: str, value: float) -> None:
    _legacy_gauge(name).set(float(value))


def inc_gauge(name: str, delta: float = 1.0) -> None:
    g = _legacy_gauge(name)
    g.inc(float(delta))
    # Legacy semantics clamped at zero.
    try:
        if g._value.get() < 0:  # noqa: SLF001 - prometheus_client has no public getter
            g.set(0.0)
    except Exception:
        pass


def render_metrics(registry: CollectorRegistry = REGISTRY) -> str:
    return generate_latest(registry).decode("utf-8")


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST


# --------------------------------------------------------------------------------------
# traceparent / request id middleware (pure ASGI)
# --------------------------------------------------------------------------------------
def parse_or_create_traceparent(raw_header: str | None) -> tuple[str, str, str]:
    """
    Parse W3C traceparent header (`00-<trace_id_32hex>-<span_id_16hex>-<flags>`)
    or generate a new trace_id and span_id. Returns (trace_id, span_id, traceparent_header).
    """
    raw = (raw_header or "").strip()
    if raw:
        parts = raw.split("-")
        if len(parts) == 4 and len(parts[1]) == 32 and len(parts[2]) == 16:
            trace_id = parts[1].lower()
            new_span_id = uuid.uuid4().hex[:16]
            return trace_id, new_span_id, f"00-{trace_id}-{new_span_id}-01"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    return trace_id, span_id, f"00-{trace_id}-{span_id}-01"


def _otel_trace_ids() -> Optional[Tuple[str, str]]:
    """(trace_id, span_id) of the active OpenTelemetry span, when tracing is on."""
    if not _tracing_active:
        return None
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx is None or not ctx.is_valid:
            return None
        return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:
        return None


_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_NUM_RE = re.compile(r"/\d+(?=/|$)")


def normalize_route(scope: dict) -> str:
    """Route template for metric labels; falls back to an id-normalised path, never raw paths."""
    route = scope.get("route")
    path = getattr(route, "path", None)
    if path:
        root = scope.get("root_path") or ""
        return f"{root}{path}" if root and not str(path).startswith(root) else str(path)
    raw = scope.get("path") or "/"
    if raw in ("/", "/health", "/ready", "/metrics"):
        return raw
    return "unmatched"


def _header(scope: dict, name: bytes) -> str:
    for k, v in scope.get("headers") or []:
        if k == name:
            return v.decode("latin-1")
    return ""


class RequestIdMiddleware:
    """Sets request/trace context, emits HTTP metrics, echoes ``X-Request-Id`` + ``traceparent``."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = _header(scope, b"x-request-id") or uuid.uuid4().hex
        trace_id, span_id, traceparent_out = parse_or_create_traceparent(
            _header(scope, b"traceparent")
        )
        otel_ids = _otel_trace_ids()
        if otel_ids is not None:
            trace_id, span_id = otel_ids
            traceparent_out = f"00-{trace_id}-{span_id}-01"
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["trace_id"] = trace_id

        tokens = (
            current_request_id_var.set(request_id),
            current_trace_id_var.set(trace_id),
            current_span_id_var.set(span_id),
            current_company_id_var.set(""),
        )

        if scope["type"] == "websocket":
            try:
                await self.app(scope, receive, send)
            finally:
                self._reset(tokens)
            return

        method = str(scope.get("method") or "GET").upper()
        status_holder = {"status": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = int(message.get("status") or 500)
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                headers.append((b"traceparent", traceparent_out.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        http_requests_in_progress.labels(method=method).inc()
        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            route = normalize_route(scope)
            http_requests_in_progress.labels(method=method).dec()
            http_requests_total.labels(
                method=method, route=route, status=str(status_holder["status"])
            ).inc()
            http_request_duration_seconds.labels(method=method, route=route).observe(elapsed)
            self._reset(tokens)

    @staticmethod
    def _reset(tokens) -> None:
        for var, tok in zip(
            (current_request_id_var, current_trace_id_var, current_span_id_var, current_company_id_var),
            tokens,
            strict=True,
        ):
            try:
                var.reset(tok)
            except Exception:
                pass


# --------------------------------------------------------------------------------------
# Structured logging
# --------------------------------------------------------------------------------------
_STD_LOG_ATTRS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName", "levelname",
        "levelno", "lineno", "message", "module", "msecs", "msg", "name", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    }
)
_REDACT_KEY_RE = re.compile(
    r"(password|passwd|secret|token|authorization|api[_-]?key|embedding|cookie|signature)",
    re.IGNORECASE,
)


def redact(value: Any, *, key: str = "") -> Any:
    """Mask credentials / biometric payloads before they reach a log sink."""
    if key and _REDACT_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > 64:
            return f"[{len(value)} items]"
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "service": SERVICE_ROLE,
            "message": record.getMessage(),
        }
        req_id = current_request_id_var.get("")
        trace_id = current_trace_id_var.get("")
        span_id = current_span_id_var.get("")
        otel_ids = _otel_trace_ids()
        if otel_ids is not None:
            trace_id, span_id = otel_ids
        company_id = current_company_id_var.get("")
        job = current_job_var.get("")
        if req_id:
            payload["requestId"] = req_id
        if trace_id:
            payload["traceId"] = trace_id
        if span_id:
            payload["spanId"] = span_id
        if company_id:
            payload["companyId"] = company_id
        if job:
            payload["job"] = job
        extras = {
            k: v for k, v in record.__dict__.items() if k not in _STD_LOG_ATTRS and not k.startswith("_")
        }
        if extras:
            payload["extra"] = redact(extras)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(service: Optional[str] = None) -> None:
    if service:
        set_service_role(service)
    level = getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter()
        if settings.LOG_JSON
        else logging.Formatter("%(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # uvicorn installs its own handlers; route them through the JSON formatter as well.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


# --------------------------------------------------------------------------------------
# OpenTelemetry tracing (optional)
# --------------------------------------------------------------------------------------
_tracing_active = False


def tracing_configured() -> bool:
    return bool(
        (os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
        or (os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or "").strip()
        or (getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "") or "").strip()
    )


def tracing_active() -> bool:
    return _tracing_active


def setup_tracing(app=None, *, service_name: Optional[str] = None, engine=None) -> bool:
    """Install the OTel SDK + OTLP exporter + instrumentations. Returns True when tracing is on.

    No-op (and no SDK import) when no OTLP endpoint is configured, so the default deployment
    pays nothing for tracing. Missing optional packages only log a warning.
    """
    global _tracing_active
    if _tracing_active:
        if app is not None:
            _instrument_app(app)
        return True
    if not tracing_configured():
        return False

    endpoint = (getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "") or "").strip()
    if endpoint:
        os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
    protocol = (
        os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL")
        or getattr(settings, "OTEL_EXPORTER_OTLP_PROTOCOL", "")
        or "http/protobuf"
    ).strip().lower()
    name = (
        service_name
        or os.environ.get("OTEL_SERVICE_NAME")
        or getattr(settings, "OTEL_SERVICE_NAME", "")
        or f"dpu-{SERVICE_ROLE}"
    )

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        if protocol.startswith("grpc"):
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        else:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError as exc:
        logger.warning("OpenTelemetry requested but SDK/exporter missing (%s); tracing disabled", exc)
        return False

    resource = Resource.create(
        {"service.name": name, "service.version": _APP_VERSION, "dpu.role": SERVICE_ROLE}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    _tracing_active = True

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:  # pragma: no cover - optional
        logger.warning("httpx instrumentation unavailable: %s", exc)

    if engine is None:
        try:
            from ..config.database import engine as _engine

            engine = _engine
        except Exception:
            engine = None
    if engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(engine=getattr(engine, "sync_engine", engine))
        except Exception as exc:  # pragma: no cover - optional
            logger.warning("SQLAlchemy instrumentation unavailable: %s", exc)

    if app is not None:
        _instrument_app(app)
    logger.info("OpenTelemetry tracing enabled service=%s protocol=%s", name, protocol)
    return True


def _instrument_app(app) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        excluded = os.environ.get("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS") or "health,ready,metrics"
        FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded)
    except Exception as exc:  # pragma: no cover - optional
        logger.warning("FastAPI instrumentation unavailable: %s", exc)


def shutdown_tracing() -> None:
    if not _tracing_active:
        return
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        shutdown = getattr(provider, "shutdown", None)
        if shutdown:
            shutdown()
    except Exception:  # pragma: no cover
        pass


# --------------------------------------------------------------------------------------
# Admin UI summary (derived from the Prometheus registry)
# --------------------------------------------------------------------------------------
def _collect_samples(prefixes: Iterable[str]):
    wanted = tuple(prefixes)
    for family in REGISTRY.collect():
        if family.name.startswith(wanted):
            for sample in family.samples:
                yield family.name, sample


def _histogram_summary(metric: str, *, scale: float = 1000.0) -> dict:
    """Aggregate a histogram family across label sets; percentiles are bucket upper bounds."""
    buckets: Dict[float, float] = {}
    count = 0.0
    total = 0.0
    for fam_name, sample in _collect_samples((metric,)):
        if fam_name != metric:
            continue
        if sample.name == f"{metric}_bucket":
            le = sample.labels.get("le", "+Inf")
            bound = float("inf") if le == "+Inf" else float(le)
            buckets[bound] = buckets.get(bound, 0.0) + sample.value
        elif sample.name == f"{metric}_count":
            count += sample.value
        elif sample.name == f"{metric}_sum":
            total += sample.value

    def pct(q: float) -> float:
        if count <= 0:
            return 0.0
        target = count * q
        for bound in sorted(buckets):
            if buckets[bound] >= target:
                return round(bound * scale, 2) if bound != float("inf") else round(total / count * scale, 2)
        return 0.0

    return {
        "count": int(count),
        "avgMs": round(total / count * scale, 2) if count else 0.0,
        "p50Ms": pct(0.50),
        "p95Ms": pct(0.95),
        "p99Ms": pct(0.99),
    }


def _gauge_value(metric: str, **labels: str) -> float:
    for _fam_name, sample in _collect_samples((metric,)):
        if sample.name == metric and all(sample.labels.get(k) == v for k, v in labels.items()):
            return float(sample.value)
    return 0.0


def get_observability_summary() -> dict:
    status_counts: Dict[str, float] = {}
    for _fam_name, sample in _collect_samples(("dpu_http_requests_total",)):
        if sample.name == "dpu_http_requests_total":
            code = sample.labels.get("status", "unknown")
            status_counts[f"http_{code}"] = status_counts.get(f"http_{code}", 0.0) + sample.value
    http_hist = _histogram_summary("dpu_http_request_duration_seconds")

    try:
        from ..utils.face_gpu_queue import face_gpu_queue_stats

        gpu_queue = face_gpu_queue_stats()
    except Exception:
        gpu_queue = {}

    try:
        from .storage_service import get_storage_status

        storage = get_storage_status()
    except Exception:
        storage = {}

    jobs: Dict[str, dict] = {}
    for _fam_name, sample in _collect_samples(("dpu_job_last_success_timestamp_seconds", "dpu_job_runs_total")):
        job = sample.labels.get("job_name")
        if not job:
            continue
        entry = jobs.setdefault(job, {"runsOk": 0, "runsError": 0, "lastSuccessAt": None})
        if sample.name == "dpu_job_last_success_timestamp_seconds" and sample.value:
            entry["lastSuccessAt"] = datetime.fromtimestamp(sample.value, tz=timezone.utc).isoformat()
        elif sample.name == "dpu_job_runs_total":
            key = "runsOk" if sample.labels.get("result") == "ok" else "runsError"
            entry[key] += int(sample.value)

    return {
        "httpRequestsTotal": int(sum(status_counts.values())),
        "httpStatusBreakdown": {k: int(v) for k, v in status_counts.items()},
        "httpAvgLatencyMs": http_hist["avgMs"],
        "activeKioskWebSockets": int(_gauge_value("dpu_ws_kiosk_connections")),
        "histograms": {
            "dpu_http_request_duration_ms": http_hist,
            "dpu_face_gpu_latency_ms": _histogram_summary("dpu_face_gpu_processing_seconds"),
            "dpu_face_gpu_queue_wait_ms": _histogram_summary("dpu_face_gpu_queue_wait_seconds"),
            "dpu_pgvector_search_ms": _histogram_summary("dpu_face_match_duration_seconds"),
        },
        "outbox": {
            "pending": int(_gauge_value("dpu_outbox_pending")),
            "oldestPendingAgeSeconds": round(_gauge_value("dpu_outbox_oldest_pending_age_seconds"), 1),
        },
        "importJobs": {
            "pending": int(_gauge_value("dpu_import_jobs_pending")),
            "running": int(_gauge_value("dpu_import_jobs_running")),
        },
        "backgroundJobs": jobs,
        "tracingEnabled": _tracing_active,
        "gpuQueue": gpu_queue,
        "storage": storage,
    }
