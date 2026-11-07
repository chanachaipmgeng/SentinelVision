from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging

from .config.database import engine, Base, async_session, ensure_db_schema
from .config.settings import settings
from .security.startup_checks import assert_runtime_secrets_configured
from .security.oidc import assert_oidc_configured
from .clients.face_core_client import assert_face_core_configured, face_core_enabled, ping_face_core
from .security.middleware import AuthzMiddleware
from .services.observability import (
    METRICS_CONTENT_TYPE,
    RequestIdMiddleware,
    configure_logging,
    render_metrics,
    set_ready_status,
    setup_tracing,
    shutdown_tracing,
)
from .services import audit_service, notification_service  # noqa: F401  register tables

# Register all ORM models on Base.metadata before create_all
from .models import (  # noqa: F401
    member,
    company,
    company_employee,
    company_location,
    department,
    position,
    employee_timestamp,
    face_encoding,
    system_setting,
    hr_schedule,
    sentinel,
    revoked_token,
)
from .models.face_encoding import prepare_pgvector, ensure_face_embedding_index
from .utils.schema_migrate import ensure_profile_and_approval_columns
from .routes import (
    member_routes,
    company_routes,
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


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    logger.exception("unhandled %s", request.url.path)
    return JSONResponse(
        {"detail": "Internal error", "requestId": getattr(request.state, "request_id", None)},
        status_code=500,
    )


# B7: outbox / retention / import processing live in the `worker` service (python -m src.worker).
# RUN_BACKGROUND_JOBS_IN_API=true runs the same job loops inside this process (single-container dev).
_in_process_jobs = None


@app.on_event("startup")
async def startup():
    from .services.storage_service import ensure_dirs
    from .services.import_job_service import import_job_root

    ensure_dirs()
    import_job_root().mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await ensure_db_schema(conn)
        await prepare_pgvector(conn)
        await conn.run_sync(Base.metadata.create_all)
        await ensure_face_embedding_index(conn)
        await ensure_profile_and_approval_columns(conn)

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
    return {"status": "ok", "queue": queue}


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
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(member_routes.router, prefix="/members", tags=["Members"])
app.include_router(company_routes.router, prefix="/companys", tags=["Companys"])
app.include_router(
    company_location_routes.router, prefix="/company-locations", tags=["Locations"]
)
app.include_router(department_routes.router, prefix="/departments", tags=["Departments"])
app.include_router(position_routes.router, prefix="/positions", tags=["Positions"])
app.include_router(employee_routes.router, prefix="/employees", tags=["Employees"])
app.include_router(
    employee_timestamp_routes.router, prefix="/timestamp", tags=["Timestamps"]
)
app.include_router(face_routes.router, prefix="/face", tags=["Face Recognition"])
app.include_router(file_upload_router.router, prefix="/api", tags=["File Upload"])
app.include_router(system_routes.router, prefix="/system")
app.include_router(dashboard_routes.router, prefix="/dashboard")
app.include_router(notification_routes.router, prefix="/notifications", tags=["Notifications"])
app.include_router(hr_routes.router, prefix="/hr", tags=["HR Schedule & PDPA"])
app.include_router(sentinel_routes.router, prefix="/sentinel", tags=["SentinelVision Security & Access"])

app.mount("/images", StaticFiles(directory="uploaded_images"), name="images")
app.mount("/enrolled_images", StaticFiles(directory="enrolled_images"), name="enrolled_images")
