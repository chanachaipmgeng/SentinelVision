"""B6 observability: prometheus_client metrics, request-id middleware, JSON logs, OTel no-op."""
from __future__ import annotations

import json
import logging
import sys

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from src.services import observability as obs


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(obs.RequestIdMiddleware)

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        logging.getLogger("dpu.test").info("handling item", extra={"itemId": item_id, "token": "x"})
        return {"id": item_id}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    @app.get("/metrics")
    async def metrics():
        return PlainTextResponse(obs.render_metrics(), media_type=obs.METRICS_CONTENT_TYPE)

    return app


def test_http_metrics_use_route_template_and_status():
    client = TestClient(_app(), raise_server_exceptions=False)
    for i in range(3):
        r = client.get(f"/items/{i}", headers={"x-request-id": f"req-{i}"})
        assert r.status_code == 200
        assert r.headers["x-request-id"] == f"req-{i}"
        assert r.headers["traceparent"].startswith("00-")
    assert client.get("/boom").status_code == 500
    assert client.get("/nope/123").status_code == 404

    text = client.get("/metrics").text
    assert 'dpu_http_requests_total{method="GET",route="/items/{item_id}",status="200"} 3.0' in text
    assert 'dpu_http_requests_total{method="GET",route="/boom",status="500"} 1.0' in text
    # Unknown paths never become label values (cardinality guard).
    assert 'route="/nope/123"' not in text
    assert 'route="unmatched",status="404"' in text
    assert 'dpu_http_request_duration_seconds_bucket{le="0.005",method="GET",route="/items/{item_id}"}' in text
    assert "dpu_http_requests_in_progress" in text


def test_metrics_endpoint_exposes_new_series_and_content_type():
    obs.observe_face_gpu_job("checkin", wait_seconds=0.01, processing_seconds=0.05, result="ok")
    obs.observe_face_gpu_job("detect", wait_seconds=0.5, processing_seconds=0.0, result="stale")
    obs.observe_face_match("pgvector_member", 0.004)
    obs.ws_kiosk_connections.inc()
    obs.set_outbox_backlog(3, None)
    obs.set_ready_status("db", True)
    with obs.track_job("retention"):
        pass
    try:
        with obs.track_job("outbox"):
            raise RuntimeError("fail once")
    except RuntimeError:
        pass

    client = TestClient(_app())
    r = client.get("/metrics")
    assert r.headers["content-type"].startswith("text/plain")
    text = r.text
    for needle in (
        'dpu_face_gpu_queue_wait_seconds_count{kind="checkin"}',
        'dpu_face_gpu_processing_seconds_bucket{kind="checkin",le="0.05"}',
        'dpu_face_gpu_jobs_total{kind="detect",result="stale"}',
        'dpu_face_match_duration_seconds_count{source="pgvector_member"}',
        "dpu_ws_kiosk_connections ",
        "dpu_outbox_pending 3.0",
        "dpu_outbox_oldest_pending_age_seconds",
        'dpu_ready_status{component="db"} 1.0',
        'dpu_job_runs_total{job_name="retention",result="ok"}',
        'dpu_job_runs_total{job_name="outbox",result="error"}',
        'dpu_job_last_success_timestamp_seconds{job_name="retention"}',
        'dpu_job_duration_seconds_count{job_name="outbox"}',
        "dpu_import_jobs_pending",
        "dpu_build_info{",
        "dpu_face_gpu_queue_pending_total",
        "dpu_face_gpu_queue_started",
    ):
        assert needle in text, needle
    if sys.platform.startswith("linux"):
        # prometheus_client's ProcessCollector reads /proc; absent on Windows/macOS dev machines.
        assert "process_cpu_seconds_total" in text
    obs.ws_kiosk_connections.dec()


def test_observability_summary_derives_from_registry():
    obs.observe_face_match("pgvector_member", 0.002)
    summary = obs.get_observability_summary()
    assert summary["histograms"]["dpu_pgvector_search_ms"]["count"] >= 1
    assert summary["histograms"]["dpu_pgvector_search_ms"]["p95Ms"] > 0
    assert "httpStatusBreakdown" in summary
    assert "outbox" in summary and "importJobs" in summary
    assert summary["tracingEnabled"] is False


def test_json_formatter_carries_correlation_and_redacts(capsys):
    client = TestClient(_app())
    formatter = obs.JsonFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    lg = logging.getLogger("dpu.test")
    lg.addHandler(handler)
    lg.setLevel(logging.INFO)
    try:
        client.get("/items/abc", headers={"x-request-id": "corr-1"})
    finally:
        lg.removeHandler(handler)
    line = [ln for ln in capsys.readouterr().err.splitlines() if "handling item" in ln][-1]
    payload = json.loads(line)
    assert payload["requestId"] == "corr-1"
    assert payload["service"] == obs.SERVICE_ROLE
    assert len(payload["traceId"]) == 32
    assert payload["extra"]["itemId"] == "abc"
    assert payload["extra"]["token"] == "[REDACTED]"

    tok = obs.set_company_context("11111111-1111-1111-1111-111111111111")
    try:
        record = logging.LogRecord("dpu.x", logging.INFO, __file__, 1, "tenant op", None, None)
        payload = json.loads(formatter.format(record))
        assert payload["companyId"] == "11111111-1111-1111-1111-111111111111"
    finally:
        obs.reset_company_context(tok)


def test_redact_masks_nested_secrets():
    out = obs.redact({"user": "a", "password": "p", "nested": {"apiKey": "k", "ok": 1}, "embedding": [0.1] * 512})
    assert out["password"] == "[REDACTED]"
    assert out["nested"]["apiKey"] == "[REDACTED]"
    assert out["nested"]["ok"] == 1
    assert out["embedding"] == "[REDACTED]"


def test_tracing_is_noop_without_endpoint(monkeypatch):
    for key in ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(obs.settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "")
    assert obs.tracing_configured() is False
    assert obs.setup_tracing(_app()) is False
    assert obs.tracing_active() is False


def test_normalize_route_prefers_route_template():
    class _Route:
        path = "/employees/company/{companyId}"

    assert obs.normalize_route({"route": _Route(), "path": "/employees/company/abc"}) == (
        "/employees/company/{companyId}"
    )
    assert obs.normalize_route({"path": "/health"}) == "/health"
    assert obs.normalize_route({"path": "/whatever/1"}) == "unmatched"
