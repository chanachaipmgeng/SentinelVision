from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging

from .config.database import engine, async_session
from .config.migrations import SchemaStatus, remediation_hint, schema_status, upgrade_to_head
from .config.settings import settings
from .security.startup_checks import assert_runtime_secrets_configured
from .security.oidc import assert_oidc_configured
from .clients.face_core_client import assert_face_core_configured, face_core_enabled, ping_face_core
from .security.middleware import AuthzMiddleware
from .schemas.error_schema import error_body, http_exception_code, sanitize_public_message
from .services.observability import (
    METRICS_CONTENT_TYPE,
    RequestIdMiddleware,
    configure_logging,
    render_metrics,
    set_ready_status,
    setup_tracing,
    shutdown_tracing,
)
from .utils.api_paths import API_V1_PREFIX
from .config import schema as _schema  # noqa: F401  registers every ORM mapper on Base.metadata
from .routes import (
    member_routes,
    company_routes,
    device_routes,
    department_routes,
    position_routes,
    employee_routes,
    employee_timestamp_routes,
    company_location_routes,
    auth_routes,
    face_routes,
    file_upload_router,
    system_routes,
    dashboard_routes,
    notification_routes,
    hr_routes,
    sentinel_routes,
)

assert_runtime_secrets_configured()
assert_oidc_configured()
assert_face_core_configured()
configure_logging("api")
logger = logging.getLogger("dpu.api")

app = FastAPI(
    title="SentinelVision Unified Biometric & Security API",
    version="4.0.0",
    redirect_slashes=False,
    docs_url="/docs" if settings.EXPOSE_API_DOCS else None,
    redoc_url="/redoc" if settings.EXPOSE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.EXPOSE_API_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthzMiddleware)
app.add_middleware(RequestIdMiddleware)
# OTel server spans wrap everything above (no-op unless OTEL_EXPORTER_OTLP_ENDPOINT is set).
setup_tracing(app, engine=engine)


def _request_id(request: Request):
    return getattr(request.state, "request_id", None)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    detail = exc.detail
    message = sanitize_public_message(detail, status_code=exc.status_code)
    details = detail if isinstance(detail, (list, dict)) and exc.status_code < 500 else None
    headers = dict(exc.headers) if exc.headers else None
    return JSONResponse(
        error_body(
            code=http_exception_code(exc.status_code, detail if isinstance(detail, str) else None),
            message=message,
            status_code=exc.status_code,
            request_id=_request_id(request),
            details=details,
        ),
        status_code=exc.status_code,
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        error_body(
            code="validation_error",
            message="Validation failed",
            status_code=422,
            request_id=_request_id(request),
            details=exc.errors(),
        ),
        status_code=422,
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("unhandled %s", request.url.path)
    return JSONResponse(
        error_body(
            code="internal_error",
            message="Internal error",
            status_code=500,
            request_id=_request_id(request),
        ),
        status_code=500,
    )


# B7: outbox / retention / import processing live in the `worker` service (python -m src.worker).
# RUN_BACKGROUND_JOBS_IN_API=true runs the same job loops inside this process (single-container dev).
_in_process_jobs = None


async def _check_schema() -> SchemaStatus:
    """Compare alembic_version with the code's head revision; never mutates the schema."""
    async with engine.connect() as conn:
        status = await schema_status(conn)
    app.state.schema_status = status
    if status.at_head:
        logger.info("schema at %s", status.head)
    else:
        logger.error("schema %s: %s", status.code, remediation_hint(status))
    return status


@app.on_event("startup")
async def startup():
    from .services.storage_service import ensure_dirs
    from .services.import_job_service import import_job_root

    ensure_dirs()
    import_job_root().mkdir(parents=True, exist_ok=True)
    # Alembic owns the schema (B1). The API only migrates when explicitly asked to.
    if settings.MIGRATE_ON_STARTUP:
        logger.info("MIGRATE_ON_STARTUP=true: running alembic upgrade head")
        await asyncio.to_thread(upgrade_to_head)
    await _check_schema()

    if not face_core_enabled():
        from .utils.face_gpu_queue import start_face_gpu_workers

        devices = settings.face_device_list()
        await start_face_gpu_workers(
            workers=max(int(settings.FACE_GPU_WORKERS), len(devices)),
            queue_size=settings.FACE_GPU_QUEUE_SIZE,
            devices=devices,
        )
    from .services.token_revocation_service import revocation_purge_loop

    asyncio.create_task(revocation_purge_loop())

    global _in_process_jobs
    if settings.RUN_BACKGROUND_JOBS_IN_API:
        from .worker import WorkerRunner

        _in_process_jobs = WorkerRunner(worker_id=f"api:{settings.WORKER_ID or 'in-process'}")
        await _in_process_jobs.start()
        logger.warning(
            "RUN_BACKGROUND_JOBS_IN_API=true: outbox/retention/import jobs run inside the API process"
        )
    else:
        logger.info("background jobs delegated to the worker service (RUN_BACKGROUND_JOBS_IN_API=false)")


@app.on_event("shutdown")
async def shutdown():
    if _in_process_jobs is not None:
        await _in_process_jobs.stop()
    shutdown_tracing()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    from sqlalchemy import text
    from .utils.face_gpu_queue import face_gpu_queue_stats

    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
    except Exception as exc:
        set_ready_status("db", False)
        return JSONResponse({"status": "down", "db": str(exc)}, status_code=503)
    set_ready_status("db", True)
    schema: SchemaStatus | None = getattr(app.state, "schema_status", None)
    if schema is not None and not schema.at_head:
        # Re-check so an operator who ran `alembic upgrade head` does not need to restart the API.
        schema = await _check_schema()
    if schema is not None and not schema.at_head and settings.REQUIRE_SCHEMA_HEAD:
        set_ready_status("schema", False)
        return JSONResponse(
            {"status": "down", "code": "schema_out_of_date", "schema": schema.as_dict()},
            status_code=503,
        )
    set_ready_status("schema", True)
    queue = {"source": "face-core"} if face_core_enabled() else face_gpu_queue_stats()
    if face_core_enabled():
        try:
            queue = await ping_face_core()
        except Exception as exc:
            set_ready_status("face_core", False)
            return JSONResponse(
                {"status": "down", "faceCore": str(exc), "code": "face_core_down"},
                status_code=503,
            )
        set_ready_status("face_core", True)
    elif not queue.get("started"):
        set_ready_status("face_queue", False)
        return JSONResponse({"status": "down", "queue": queue}, status_code=503)
    else:
        set_ready_status("face_queue", True)
    return {"status": "ok", "queue": queue, "schema": schema.as_dict() if schema else None}


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(render_metrics(), media_type=METRICS_CONTENT_TYPE)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the API",
        "face": (
            "Face Core BFF"
            if face_core_enabled()
            else "InsightFace buffalo_l + pgvector"
        ),
    }
def _mount_api(prefix: str = "") -> None:
    """Mount the public HTTP surface at ``prefix`` ('' or '/api/v1')."""
    p = prefix.rstrip("/")
    app.include_router(auth_routes.router, prefix=f"{p}/auth", tags=["Authentication"])
    app.include_router(member_routes.router, prefix=f"{p}/members", tags=["Members"])
    # D6: keep /companys (legacy typo) and add /companies as the canonical spelling.
    app.include_router(company_routes.router, prefix=f"{p}/companys", tags=["Companys"])
    app.include_router(company_routes.router, prefix=f"{p}/companies", tags=["Companies"])
    app.include_router(device_routes.router, prefix=f"{p}/devices", tags=["Kiosk Devices"])
    app.include_router(
        company_location_routes.router, prefix=f"{p}/company-locations", tags=["Locations"]
    )
    app.include_router(department_routes.router, prefix=f"{p}/departments", tags=["Departments"])
    app.include_router(position_routes.router, prefix=f"{p}/positions", tags=["Positions"])
    app.include_router(employee_routes.router, prefix=f"{p}/employees", tags=["Employees"])
    app.include_router(
        employee_timestamp_routes.router, prefix=f"{p}/timestamp", tags=["Timestamps"]
    )
    app.include_router(face_routes.router, prefix=f"{p}/face", tags=["Face Recognition"])
    app.include_router(system_routes.router, prefix=f"{p}/system")
    app.include_router(dashboard_routes.router, prefix=f"{p}/dashboard")
    app.include_router(
        notification_routes.router, prefix=f"{p}/notifications", tags=["Notifications"]
    )
    app.include_router(hr_routes.router, prefix=f"{p}/hr", tags=["HR Schedule & PDPA"])
    app.include_router(
        sentinel_routes.router, prefix=f"{p}/sentinel", tags=["SentinelVision Security & Access"]
    )


# Legacy root paths (SPA / kiosk continue to work unchanged).
_mount_api("")
# D6 versioned alias — identical handlers under /api/v1.
_mount_api(API_V1_PREFIX)
# File upload stays under /api (and /api/v1/api would be awkward); mount once at /api.
app.include_router(file_upload_router.router, prefix="/api", tags=["File Upload"])
app.include_router(
    file_upload_router.router, prefix=f"{API_V1_PREFIX}/files", tags=["File Upload"]
)

app.mount("/images", StaticFiles(directory="uploaded_images"), name="images")
app.mount("/enrolled_images", StaticFiles(directory="enrolled_images"), name="enrolled_images")
