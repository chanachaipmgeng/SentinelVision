from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging

from .config.database import engine, Base, async_session
from .config.settings import settings
from .security.jwt import assert_secret_configured
from .security.middleware import AuthzMiddleware
from .services.observability import RequestIdMiddleware, configure_logging, render_metrics
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
)

assert_secret_configured()
configure_logging()
logger = logging.getLogger("dpu.api")

app = FastAPI(
    title="DPU Attendance API",
    version="2.1.0",
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


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    logger.exception("unhandled %s", request.url.path)
    return JSONResponse(
        {"detail": "Internal error", "requestId": getattr(request.state, "request_id", None)},
        status_code=500,
    )


async def _retention_loop() -> None:
    from .services.storage_service import retention_tick

    while True:
        try:
            logger.info("retention %s", retention_tick())
        except Exception:
            logger.exception("retention failed")
        await asyncio.sleep(3600)


async def _notify_loop() -> None:
    from .services.notification_service import drain_outbox

    while True:
        try:
            await drain_outbox()
        except Exception:
            logger.exception("notify drain failed")
        await asyncio.sleep(max(5, int(settings.NOTIFY_POLL_SECONDS)))


@app.on_event("startup")
async def startup():
    from .services.storage_service import ensure_dirs

    ensure_dirs()
    async with engine.begin() as conn:
        await prepare_pgvector(conn)
        await conn.run_sync(Base.metadata.create_all)
        await ensure_face_embedding_index(conn)
        await ensure_profile_and_approval_columns(conn)

    if not settings.FACE_CORE_ENABLED:
        from .utils.face_gpu_queue import start_face_gpu_workers

        devices = settings.face_device_list()
        await start_face_gpu_workers(
            workers=max(int(settings.FACE_GPU_WORKERS), len(devices)),
            queue_size=settings.FACE_GPU_QUEUE_SIZE,
            devices=devices,
        )
    asyncio.create_task(_retention_loop())
    asyncio.create_task(_notify_loop())


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
        return JSONResponse({"status": "down", "db": str(exc)}, status_code=503)
    queue = face_gpu_queue_stats()
    if not settings.FACE_CORE_ENABLED and not queue.get("started"):
        return JSONResponse({"status": "down", "queue": queue}, status_code=503)
    return {"status": "ok", "queue": queue}


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the API",
        "face": (
            "Face Core BFF"
            if settings.FACE_CORE_ENABLED
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

app.mount("/images", StaticFiles(directory="uploaded_images"), name="images")
app.mount("/enrolled_images", StaticFiles(directory="enrolled_images"), name="enrolled_images")
