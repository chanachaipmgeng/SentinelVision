"""SentinelVision HTTP routes (thin) — orchestration in controllers/services.

Stable re-exports for F3 / face_ws / worker / tests:
``evaluate_kiosk_sentinel_match``, ``evaluate_unified_scan_decision``,
``resolve_scan_zone``, ``maybe_dispatch_zone_relay``, ``expire_sentinel_identities_tick``,
and serializer / schedule helpers.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..controllers import sentinel_controller as ctrl
from ..security.deps import assert_request_company_access, current_member_var
from ..services.company_module_service import (
    get_company_module_config,
    save_company_module_config,
)
from ..services.face_match_service import search_sentinel_identity_pgvector  # noqa: F401 — test shim
from ..services.sentinel_identity_service import (
    VALID_IDENTITY_TYPES,
    VALID_SEVERITIES,
    VALID_STATION_MODES,
    bangkok_tz as _bangkok_tz,
    expire_sentinel_identities_tick,
    is_within_schedule as _is_within_schedule,
    parse_iso_dt as _parse_iso_dt,
    serialize_event as _serialize_event,
    serialize_identity as _serialize_identity,
    serialize_zone as _serialize_zone,
)
from ..services.incident_sla_service import (
    get_incident_sla_settings,
    put_incident_sla_settings,
)
from ..services.sentinel_incident_service import (
    acknowledge_incident,
    acknowledge_incidents_bulk,
    assign_incident,
    close_incident,
    close_incidents_bulk,
    dispatch_relay_webhook_async as _dispatch_relay_webhook_async,
    evaluate_kiosk_sentinel_match,
    evaluate_unified_scan_decision,
    list_incidents,
    maybe_dispatch_zone_relay,
    resolve_scan_zone,
    serialize_incident as _serialize_incident,
)
from ..services.sentinel_muster_service import build_muster_roll
from ..services.siem_export_service import (
    enqueue_siem_test,
    get_siem_settings,
    queue_siem_incident_export,
    save_siem_settings,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Re-exports (stable import paths for face_controller / face_ws / worker / tests)
# ---------------------------------------------------------------------------
__all__ = [
    "router",
    "evaluate_kiosk_sentinel_match",
    "evaluate_unified_scan_decision",
    "expire_sentinel_identities_tick",
    "maybe_dispatch_zone_relay",
    "resolve_scan_zone",
    "search_sentinel_identity_pgvector",
    "_bangkok_tz",
    "_is_within_schedule",
    "_serialize_event",
    "_serialize_identity",
    "_serialize_incident",
    "_serialize_zone",
    "_parse_iso_dt",
    "_dispatch_relay_webhook_async",
    "VALID_IDENTITY_TYPES",
    "VALID_SEVERITIES",
    "VALID_STATION_MODES",
    "queue_siem_incident_export",
    "build_muster_roll",
]


@router.get("/company/{companyId}/module-config")
async def get_company_module_config_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await get_company_module_config(db, companyId)


@router.put("/company/{companyId}/module-config")
async def put_company_module_config_route(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await save_company_module_config(db, companyId, body or {})


@router.get("/company/{companyId}/overview")
async def get_sentinel_overview(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.get_overview(db, companyId)


@router.get("/company/{companyId}/muster")
async def get_sentinel_muster(
    companyId: UUID,
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated emergency muster roll (PRESENT daily / open presence / visitors)."""
    await assert_request_company_access(request, db, companyId)
    return await build_muster_roll(db, companyId, limit=limit, offset=offset)


@router.get("/company/{companyId}/siem-settings")
async def get_company_siem_settings(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await get_siem_settings(db, companyId)


@router.put("/company/{companyId}/siem-settings")
async def put_company_siem_settings(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await save_siem_settings(db, companyId, body or {})


@router.post("/company/{companyId}/siem-settings/test")
async def test_company_siem_settings(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    _ = await get_siem_settings(db, companyId)
    return await enqueue_siem_test(companyId)


@router.get("/company/{companyId}/identities")
async def list_sentinel_identities(
    companyId: UUID,
    request: Request,
    identityType: Optional[str] = Query(None),
    eventId: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.list_identities(
        db, companyId, identity_type=identityType, event_id=eventId, limit=limit, offset=offset
    )


@router.post("/company/{companyId}/identities")
async def create_sentinel_identity(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.create_identity(db, companyId, body)


@router.put("/company/{companyId}/identities/{identityId}")
async def update_sentinel_identity(
    companyId: UUID,
    identityId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.update_identity(db, companyId, identityId, body)


@router.delete("/company/{companyId}/identities/{identityId}")
async def delete_sentinel_identity(
    companyId: UUID,
    identityId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.delete_identity(db, companyId, identityId)


@router.post("/company/{companyId}/identities/{identityId}/enroll-face")
async def enroll_sentinel_identity_face(
    companyId: UUID,
    identityId: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.enroll_identity_face(db, companyId, identityId, file)


@router.get("/company/{companyId}/zones")
async def list_access_zones(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.list_zones(db, companyId)


@router.post("/company/{companyId}/zones")
async def create_access_zone(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.create_zone(db, companyId, body)


@router.put("/company/{companyId}/zones/{zoneId}")
async def update_access_zone(
    companyId: UUID,
    zoneId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.update_zone(db, companyId, zoneId, body)


@router.delete("/company/{companyId}/zones/{zoneId}")
async def delete_access_zone(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.delete_zone(db, companyId, zoneId)


@router.post("/company/{companyId}/zones/{zoneId}/trigger")
async def trigger_zone_door_relay(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.trigger_zone(db, companyId, zoneId, body)


@router.get("/company/{companyId}/events")
async def list_sentinel_events(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.list_events(db, companyId)


@router.post("/company/{companyId}/events")
async def create_sentinel_event(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.create_event(db, companyId, body)


@router.delete("/company/{companyId}/events/{eventId}")
async def delete_sentinel_event(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.delete_event(db, companyId, eventId)


@router.post("/company/{companyId}/scan")
async def unified_sentinel_scan(
    companyId: UUID,
    request: Request,
    file: UploadFile = File(...),
    zoneId: Optional[str] = Form(None),
    eventId: Optional[str] = Form(None),
    stationMode: str = Form("ACCESS_CONTROL"),
    totpOrPin: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.unified_scan(
        db,
        companyId,
        file,
        zone_id=zoneId,
        event_id=eventId,
        station_mode=stationMode,
        totp_or_pin=totpOrPin,
    )


@router.get("/company/{companyId}/incident-sla-settings")
async def get_company_incident_sla_settings(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await get_incident_sla_settings(db, companyId)


@router.put("/company/{companyId}/incident-sla-settings")
async def put_company_incident_sla_settings(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await put_incident_sla_settings(db, companyId, body or {})


@router.get("/company/{companyId}/incidents")
async def list_sentinel_incidents(
    companyId: UUID,
    request: Request,
    eventType: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    zoneId: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await list_incidents(
        db,
        companyId,
        event_type=eventType,
        severity=severity,
        status_filter=status,
        zone_id=zoneId,
        limit=limit,
        offset=offset,
    )


@router.post("/company/{companyId}/incidents/bulk-acknowledge")
async def bulk_acknowledge_sentinel_incidents(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    actor = current_member_var.get()
    return await acknowledge_incidents_bulk(
        db,
        companyId,
        (body or {}).get("incidentIds"),
        actor.memberId if actor else None,
    )


@router.post("/company/{companyId}/incidents/bulk-close")
async def bulk_close_sentinel_incidents(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    actor = current_member_var.get()
    return await close_incidents_bulk(
        db,
        companyId,
        (body or {}).get("incidentIds"),
        actor.memberId if actor else None,
    )


@router.post("/company/{companyId}/incidents/{incidentId}/acknowledge")
async def acknowledge_sentinel_incident(
    companyId: UUID,
    incidentId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    actor = current_member_var.get()
    inc = await acknowledge_incident(
        db, companyId, incidentId, actor.memberId if actor else None
    )
    return _serialize_incident(inc)


@router.post("/company/{companyId}/incidents/{incidentId}/assign")
async def assign_sentinel_incident(
    companyId: UUID,
    incidentId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    actor = current_member_var.get()
    assignee_raw = (body or {}).get("assignedTo") or (body or {}).get("assigneeId")
    assignee_id = UUID(str(assignee_raw)) if assignee_raw else None
    inc = await assign_incident(
        db,
        companyId,
        incidentId,
        actor_id=actor.memberId if actor else None,
        assignee_id=assignee_id,
    )
    return _serialize_incident(inc)


@router.post("/company/{companyId}/incidents/{incidentId}/close")
async def close_sentinel_incident(
    companyId: UUID,
    incidentId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    actor = current_member_var.get()
    inc = await close_incident(
        db, companyId, incidentId, actor.memberId if actor else None
    )
    return _serialize_incident(inc)


@router.get("/company/{companyId}/edge-sync")
async def get_edge_sync_manifest(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.edge_sync_manifest(db, companyId)
