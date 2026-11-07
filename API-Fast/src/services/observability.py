"""Observability: W3C traceparent / request id context, JSON logs, Prometheus histograms & gauges."""
from __future__ import annotations

from collections import Counter
from contextvars import ContextVar
import json
import logging
import threading
import time
import uuid
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..config.settings import settings

current_request_id_var: ContextVar[str] = ContextVar("dpu_request_id", default="")
current_trace_id_var: ContextVar[str] = ContextVar("dpu_trace_id", default="")

_lock = threading.Lock()
_metrics = Counter()
_latency_ms = 0.0
_latency_n = 0

_HISTOGRAM_BUCKETS: Tuple[float, ...] = (5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0)


class _HistogramState:
    def __init__(self, buckets: Tuple[float, ...] = _HISTOGRAM_BUCKETS) -> None:
        self.buckets = buckets
        self.counts: List[int] = [0 for _ in buckets]
        self.count_total: int = 0
        self.sum_total: float = 0.0
        self.max_val: float = 0.0

    def observe(self, val: float) -> None:
        v = max(0.0, float(val))
        self.count_total += 1
        self.sum_total += v
        if v > self.max_val:
            self.max_val = v
        for idx, bound in enumerate(self.buckets):
            if v <= bound:
                self.counts[idx] += 1

    def approx_percentile(self, q: float) -> float:
        if self.count_total == 0:
            return 0.0
        target = self.count_total * q
        for idx, bound in enumerate(self.buckets):
            if self.counts[idx] >= target:
                return bound
        return round(self.max_val, 2)


_histograms: Dict[str, _HistogramState] = {
    "dpu_http_request_duration_ms": _HistogramState(),
    "dpu_face_gpu_latency_ms": _HistogramState(),
    "dpu_pgvector_search_ms": _HistogramState(),
}

_gauges: Dict[str, float] = {
    "dpu_ws_active_kiosks": 0.0,
}


def observe_histogram(name: str, value_ms: float) -> None:
    with _lock:
        hist = _histograms.get(name)
        if hist is None:
            hist = _HistogramState()
            _histograms[name] = hist
        hist.observe(value_ms)


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = float(value)


def inc_gauge(name: str, delta: float = 1.0) -> None:
    with _lock:
        _gauges[name] = max(0.0, float(_gauges.get(name, 0.0)) + float(delta))


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


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _latency_ms, _latency_n
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        trace_id, _span_id, traceparent_out = parse_or_create_traceparent(
            request.headers.get("traceparent")
        )
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        tok_req = current_request_id_var.set(request_id)
        tok_trace = current_trace_id_var.set(trace_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            current_request_id_var.reset(tok_req)
            current_trace_id_var.reset(tok_trace)

        elapsed = (time.perf_counter() - start) * 1000.0
        with _lock:
            _latency_ms += elapsed
            _latency_n += 1
            _metrics[f"http_{response.status_code}"] += 1
        observe_histogram("dpu_http_request_duration_ms", elapsed)
        response.headers["X-Request-Id"] = request_id
        response.headers["traceparent"] = traceparent_out
        return response


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        req_id = current_request_id_var.get("")
        trace_id = current_trace_id_var.get("")
        if req_id:
            payload["requestId"] = req_id
        if trace_id:
            payload["traceId"] = trace_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
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


def render_metrics() -> str:
    lines = [
        "# HELP dpu_http_requests_total HTTP responses",
        "# TYPE dpu_http_requests_total counter",
    ]
    with _lock:
        metrics_items = list(_metrics.items())
        avg = (_latency_ms / _latency_n) if _latency_n else 0.0
        gauges_snapshot = dict(_gauges)
        hist_snapshots = {
            name: (
                list(h.buckets),
                list(h.counts),
                h.count_total,
                h.sum_total,
            )
            for name, h in _histograms.items()
        }

    for key, value in metrics_items:
        lines.append(f'dpu_http_requests_total{{code="{key}"}} {value}')
    lines.append("# HELP dpu_http_latency_ms_avg Average request latency")
    lines.append("# TYPE dpu_http_latency_ms_avg gauge")
    lines.append(f"dpu_http_latency_ms_avg {avg:.2f}")

    # Live GPU queue gauges
    try:
        from ..utils.face_gpu_queue import face_gpu_queue_stats

        q = face_gpu_queue_stats()
        gauges_snapshot["dpu_face_gpu_pending_jobs"] = float(q.get("pending") or 0)
        gauges_snapshot["dpu_face_gpu_active_workers"] = float(q.get("active") or 0)
        gauges_snapshot["dpu_face_gpu_completed_total"] = float(q.get("completed") or 0)
    except Exception:
        pass

    for g_name, g_val in gauges_snapshot.items():
        lines.append(f"# HELP {g_name} Live operational gauge")
        lines.append(f"# TYPE {g_name} gauge")
        lines.append(f"{g_name} {g_val:.2f}")

    for h_name, (buckets, counts, count_total, sum_total) in hist_snapshots.items():
        lines.append(f"# HELP {h_name} Latency histogram in milliseconds")
        lines.append(f"# TYPE {h_name} histogram")
        for idx, bound in enumerate(buckets):
            lines.append(f'{h_name}_bucket{{le="{bound:g}"}} {counts[idx]}')
        lines.append(f'{h_name}_bucket{{le="+Inf"}} {count_total}')
        lines.append(f"{h_name}_sum {sum_total:.2f}")
        lines.append(f"{h_name}_count {count_total}")

    return "\n".join(lines) + "\n"


def get_observability_summary() -> dict:
    with _lock:
        avg = (_latency_ms / _latency_n) if _latency_n else 0.0
        http_counts = dict(_metrics)
        gauges_snapshot = dict(_gauges)
        hist_summary = {}
        for name, h in _histograms.items():
            hist_summary[name] = {
                "count": h.count_total,
                "avgMs": round(h.sum_total / h.count_total, 2) if h.count_total else 0.0,
                "p50Ms": h.approx_percentile(0.50),
                "p95Ms": h.approx_percentile(0.95),
                "maxMs": round(h.max_val, 2),
            }

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

    return {
        "httpRequestsTotal": sum(http_counts.values()),
        "httpStatusBreakdown": http_counts,
        "httpAvgLatencyMs": round(avg, 2),
        "activeKioskWebSockets": int(gauges_snapshot.get("dpu_ws_active_kiosks", 0)),
        "histograms": hist_summary,
        "gpuQueue": gpu_queue,
        "storage": storage,
    }
