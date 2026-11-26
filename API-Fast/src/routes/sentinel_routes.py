"""SentinelVision HTTP routes (thin) — orchestration in controllers/services.

Stable re-exports for F3 / face_ws / worker / tests:
``evaluate_kiosk_sentinel_match``, ``evaluate_unified_scan_decision``,
``resolve_scan_zone``, ``maybe_dispatch_zone_relay``, ``expire_sentinel_identities_tick``,
and serializer / schedule helpers.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..controllers import sentinel_controller as ctrl
from ..security.deps import (
    assert_request_company_access,
    assert_request_permission,
    current_member_var,
    require_request_system_admin,
)
from ..services import rbac_service
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
    enrich_incidents_location_metadata,
    evaluate_kiosk_sentinel_match,
    evaluate_unified_scan_decision,
    list_incidents,
    maybe_dispatch_zone_relay,
    resolve_scan_zone,
    serialize_incident as _serialize_incident,
)
from ..services.sentinel_muster_service import build_muster_roll
from ..services.sentinel_graph_service import build_sentinel_investigation_graph
from ..services.sentinel_assistant_service import stream_assistant_chat
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
    await assert_request_permission(request, db, rbac_service.PERM_COMPANY_SETTINGS, companyId)
    return await save_company_module_config(db, companyId, body or {})


@router.get("/company/{companyId}/overview")
async def get_sentinel_overview(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.get_overview(db, companyId)


@router.get("/company/{companyId}/graph")
async def get_sentinel_investigation_graph(
    companyId: UUID,
    request: Request,
    days: int = Query(7, ge=1, le=90),
    limit_incidents: int = Query(40, ge=5, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Company-scoped ECharts 2D relationship graph (Zone ↔ Camera ↔ Identity ↔ Incident)."""
    await assert_request_company_access(request, db, companyId)
    return await build_sentinel_investigation_graph(
        db,
        companyId,
        days=days,
        limit_incidents=limit_incidents,
    )


@router.post("/company/{companyId}/assistant/chat")
async def post_sentinel_assistant_chat(
    companyId: UUID,
    body: dict,
    request: Request,
):
    """Company-scoped Security & HR AI Copilot (SSE stream; releases DB session before streaming)."""
    from ..config.database import async_session
    from ..services.sentinel_assistant_service import collect_company_snapshot

    async with async_session() as db:
        await assert_request_company_access(request, db, companyId)
        snapshot = await collect_company_snapshot(db, companyId)
    question = str((body or {}).get("question") or "").strip()
    history = (body or {}).get("history")
    if not isinstance(history, list):
        history = []
    return StreamingResponse(
        stream_assistant_chat(None, companyId, question, history, snapshot=snapshot),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
    await assert_request_permission(request, db, rbac_service.PERM_COMPANY_SETTINGS, companyId)
    return await get_siem_settings(db, companyId)


@router.put("/company/{companyId}/siem-settings")
async def put_company_siem_settings(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_COMPANY_SETTINGS, companyId)
    return await save_siem_settings(db, companyId, body or {})


@router.post("/company/{companyId}/siem-settings/test")
async def test_company_siem_settings(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_COMPANY_SETTINGS, companyId)
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
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.create_identity(db, companyId, body)


@router.put("/company/{companyId}/identities/{identityId}")
async def update_sentinel_identity(
    companyId: UUID,
    identityId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.update_identity(db, companyId, identityId, body)


@router.delete("/company/{companyId}/identities/{identityId}")
async def delete_sentinel_identity(
    companyId: UUID,
    identityId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.delete_identity(db, companyId, identityId)


@router.post("/company/{companyId}/identities/{identityId}/enroll-face")
async def enroll_sentinel_identity_face(
    companyId: UUID,
    identityId: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
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
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.create_zone(db, companyId, body)


@router.put("/company/{companyId}/zones/{zoneId}")
async def update_access_zone(
    companyId: UUID,
    zoneId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.update_zone(db, companyId, zoneId, body)


@router.delete("/company/{companyId}/zones/{zoneId}")
async def delete_access_zone(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.delete_zone(db, companyId, zoneId)


@router.post("/company/{companyId}/zones/{zoneId}/trigger")
async def trigger_zone_door_relay(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.trigger_zone(db, companyId, zoneId, body)


@router.post("/company/{companyId}/zones/{zoneId}/evaluate-access")
async def evaluate_zone_access_route(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.evaluate_zone_access(db, companyId, zoneId, body)


@router.post("/company/{companyId}/zones/{zoneId}/edge-unlock")
async def edge_unlock_zone_route(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.edge_unlock_zone(db, companyId, zoneId, body)


@router.post("/company/{companyId}/health-check")
async def run_company_health_check_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.run_company_health_check(db, companyId)


@router.post("/company/{companyId}/reindex-vectors")
async def reindex_company_vectors_route(
    companyId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_COMPANY_SETTINGS, companyId)
    return await ctrl.reindex_company_vectors(db, companyId, body)


@router.get("/company/{companyId}/reindex-status")
async def get_reindex_status_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.get_reindex_status(db, companyId)


@router.post("/company/{companyId}/fire-alarm")
async def trigger_company_fire_alarm(
    companyId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.trigger_fire_alarm(db, companyId, body)


@router.post("/company/{companyId}/fire-alarm/reset")
async def reset_company_fire_alarm(
    companyId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.reset_fire_alarm(db, companyId, body)


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
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.create_event(db, companyId, body)


@router.delete("/company/{companyId}/events/{eventId}")
async def delete_sentinel_event(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await ctrl.delete_event(db, companyId, eventId)


@router.post("/company/{companyId}/events/{eventId}/sessions/check-in")
async def checkin_event_breakout_session(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_session_service import check_in_breakout_room

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    id_raw = body.get("identityId")
    return await check_in_breakout_room(
        db,
        company_id=companyId,
        event_id=eventId,
        room_code=str(body.get("roomCode") or ""),
        capacity=int(body.get("capacity") or 50),
        subject_name=str(body.get("subjectName") or "Attendee"),
        identity_id=UUID(str(id_raw)) if id_raw else None,
    )


@router.patch("/company/{companyId}/events/{eventId}/registration")
async def update_event_reg_settings(
    companyId: UUID,
    eventId: UUID,
    body: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_registration_service import update_event_registration_settings

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await update_event_registration_settings(db, companyId, eventId, body)


@router.get("/company/{companyId}/events/{eventId}/registrations")
async def list_event_regs(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_registration_service import list_event_registrations

    await assert_request_company_access(request, db, companyId)
    return await list_event_registrations(
        db, companyId, eventId, limit=limit, offset=offset, search=search, status_filter=status
    )


@router.get("/company/{companyId}/events/{eventId}/registrations/export")
async def export_event_regs_csv(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import PlainTextResponse
    from ..services.event_registration_service import export_event_registrations_csv

    await assert_request_company_access(request, db, companyId)
    csv_content = await export_event_registrations_csv(db, companyId, eventId)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="event_{eventId}_registrations.csv"'},
    )


@router.post("/company/{companyId}/events/{eventId}/registrations/{registrationId}/cancel")
async def cancel_event_reg(
    companyId: UUID,
    eventId: UUID,
    registrationId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_registration_service import cancel_event_registration

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await cancel_event_registration(db, companyId, eventId, registrationId)


@router.get("/company/{companyId}/fleet-health")
async def get_fleet_health(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.fleet_health_service import get_fleet_health_overview

    await assert_request_company_access(request, db, companyId)
    return await get_fleet_health_overview(db, companyId)


@router.get("/public/events/{slug}")
async def get_public_event(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_registration_service import get_public_event_by_slug

    return await get_public_event_by_slug(db, slug)


@router.post("/public/events/{slug}/register")
async def register_event_publicly(
    slug: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_registration_service import register_public_event

    return await register_public_event(db, slug, body)


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
    await assert_request_permission(request, db, rbac_service.PERM_COMPANY_SETTINGS, companyId)
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
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
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
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
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
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    actor = current_member_var.get()
    inc = await acknowledge_incident(
        db, companyId, incidentId, actor.memberId if actor else None
    )
    s = _serialize_incident(inc)
    enriched = await enrich_incidents_location_metadata(db, companyId, [s])
    return enriched[0] if enriched else s


@router.post("/company/{companyId}/incidents/{incidentId}/assign")
async def assign_sentinel_incident(
    companyId: UUID,
    incidentId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
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
    s = _serialize_incident(inc)
    enriched = await enrich_incidents_location_metadata(db, companyId, [s])
    return enriched[0] if enriched else s


@router.post("/company/{companyId}/incidents/{incidentId}/close")
async def close_sentinel_incident(
    companyId: UUID,
    incidentId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    actor = current_member_var.get()
    inc = await close_incident(
        db, companyId, incidentId, actor.memberId if actor else None
    )
    s = _serialize_incident(inc)
    enriched = await enrich_incidents_location_metadata(db, companyId, [s])
    return enriched[0] if enriched else s


@router.get("/company/{companyId}/edge-sync")
async def get_edge_sync_manifest(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.edge_sync_manifest(db, companyId)


@router.get("/company/{companyId}/audit-verify")
async def verify_company_audit_chain(
    companyId: UUID,
    request: Request,
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    from ..services.audit_service import verify_audit_chain

    await assert_request_permission(request, db, rbac_service.PERM_AUDIT_READ, companyId)
    return await verify_audit_chain(db, companyId, limit=limit)


@router.post("/company/{companyId}/zones/{zoneId}/door-telemetry")
async def post_zone_door_telemetry(
    companyId: UUID,
    zoneId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.report_door_telemetry(db, companyId, zoneId, body or {})


@router.post("/company/{companyId}/visitors/invite")
async def create_visitor_invite(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.visitor_invite_service import create_visitor_invite_token

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    payload = body or {}
    return create_visitor_invite_token(
        company_id=companyId,
        visitor_name=str(payload.get("visitorName") or ""),
        host_name=payload.get("hostName"),
        purpose=payload.get("purpose"),
        valid_hours=int(payload.get("validHours") or 12),
        invite_ttl_hours=int(payload.get("inviteTtlHours") or 72),
    )


@router.get("/public/visitor-invite/{token}")
async def get_public_visitor_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    from ..services.pdpa_service import get_consent_policy
    from ..services.visitor_invite_service import verify_visitor_invite_token

    invite = verify_visitor_invite_token(token)
    policy = await get_consent_policy(db, invite["companyId"])
    return {
        "visitorName": invite["visitorName"],
        "hostName": invite["hostName"],
        "purpose": invite["purpose"],
        "validHours": invite["validHours"],
        "expiresAt": invite["expiresAt"],
        "consentPolicy": policy,
    }


@router.post("/public/visitor-invite/{token}/complete")
async def complete_public_visitor_invite(
    token: str,
    consentAccepted: bool = Form(...),
    phoneNumber: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException
    from ..services.visitor_invite_service import (
        create_visitor_pass_token,
        verify_visitor_invite_token,
    )

    if not consentAccepted:
        raise HTTPException(status_code=400, detail="PDPA biometric consent is required")
    invite = verify_visitor_invite_token(token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=int(invite["validHours"]))
    created = await ctrl.create_identity(
        db,
        invite["companyId"],
        {
            "identityType": "VISITOR",
            "fullName": invite["visitorName"],
            "hostName": invite["hostName"],
            "purpose": invite["purpose"],
            "phoneNumber": phoneNumber,
            "validFrom": now.isoformat(),
            "expiresAt": expires_at.isoformat(),
            "consentAccepted": True,
        },
    )
    if photo is not None:
        created = await ctrl.enroll_identity_face(
            db, invite["companyId"], UUID(created["identityId"]), photo
        )
    pass_info = create_visitor_pass_token(
        company_id=invite["companyId"],
        identity_id=UUID(created["identityId"]),
        visitor_name=invite["visitorName"],
        valid_from=now,
        expires_at=expires_at,
        zone_ids=created.get("allowedZoneIds") or [],
    )
    return {"registered": True, "identity": created, "pass": pass_info}


@router.post("/company/{companyId}/visitors/verify-pass")
async def verify_visitor_digital_pass(
    companyId: UUID,
    request: Request,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from sqlalchemy import select
    from ..models.sentinel import SentinelIdentity
    from ..services.visitor_invite_service import verify_visitor_pass_token

    await assert_request_company_access(request, db, companyId)
    pass_code = str((body or {}).get("passCode") or "").strip()
    if not pass_code:
        raise HTTPException(status_code=400, detail="passCode is required")

    pass_payload = verify_visitor_pass_token(pass_code)
    if pass_payload["companyId"] != companyId:
        raise HTTPException(status_code=403, detail="Pass belongs to another organization")

    stmt = select(SentinelIdentity).where(
        SentinelIdentity.identityId == pass_payload["identityId"],
        SentinelIdentity.companyId == companyId,
        SentinelIdentity.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    identity = res.scalar_one_or_none()
    if not identity:
        raise HTTPException(status_code=404, detail="Visitor identity not found or revoked")
    if identity.status != "ACTIVE":
        raise HTTPException(status_code=403, detail=f"Visitor status is {identity.status}")

    return {
        "valid": True,
        "passCode": pass_code,
        "identityId": str(identity.identityId),
        "fullName": identity.fullName,
        "identityType": identity.identityType,
        "status": identity.status,
        "validFrom": pass_payload["validFrom"],
        "expiresAt": pass_payload["expiresAt"],
        "visitPurpose": identity.visitPurpose,
        "hostMemberId": str(identity.hostMemberId) if identity.hostMemberId else None,
        "allowedZoneIds": identity.allowedZoneIds or [],
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/public/visitor-invite/{token}/ocr-document")
async def ocr_public_visitor_document(
    token: str,
    file: Optional[UploadFile] = File(None),
    ocrText: Optional[str] = Form(None),
    documentType: str = Form("AUTO"),
):
    from ..services.id_ocr_service import extract_document_from_image
    from ..services.visitor_invite_service import verify_visitor_invite_token

    verify_visitor_invite_token(token)
    img_bytes = await file.read() if file is not None else None
    parsed = await extract_document_from_image(
        image_bytes=img_bytes,
        ocr_text=ocrText,
        document_type=documentType,
    )
    return {"ok": True, "document": parsed}


@router.post("/company/{companyId}/visitors/ocr-document")
async def ocr_company_visitor_document(
    companyId: UUID,
    request: Request,
    file: Optional[UploadFile] = File(None),
    ocrText: Optional[str] = Form(None),
    documentType: str = Form("AUTO"),
    db: AsyncSession = Depends(get_db),
):
    from ..services.id_ocr_service import extract_document_from_image

    await assert_request_company_access(request, db, companyId)
    img_bytes = await file.read() if file is not None else None
    parsed = await extract_document_from_image(
        image_bytes=img_bytes,
        ocr_text=ocrText,
        document_type=documentType,
    )
    return {"ok": True, "companyId": str(companyId), "document": parsed}


@router.websocket("/ws/incidents/{companyId}")
async def sentinel_incidents_ws(websocket: WebSocket, companyId: UUID):
    """Real-time security/watchlist incident push stream for Security Command Center."""
    import asyncio
    import time

    from ..config.database import async_session
    from ..config.settings import settings
    from ..models.member import Member, StatusType
    from ..security.deps import assert_company_access
    from ..security.jwt import decode_token
    from ..services.incident_ws_hub import incident_ws_hub
    from ..services.token_revocation_service import is_token_revoked

    token = websocket.cookies.get("dpu_access_token")
    if not token:
        auth_header = websocket.headers.get("authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token and getattr(settings, "WS_ALLOW_QUERY_TOKEN", True):
        token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_token(token, expected_typ="access")
        raw_mid = payload.get("memberId") or payload.get("sub")
        if not raw_mid:
            await websocket.close(code=4401)
            return
        member_id = UUID(str(raw_mid))
        if await is_token_revoked(payload):
            await websocket.close(code=4401)
            return
    except Exception:
        await websocket.close(code=4401)
        return

    async with async_session() as db:
        member = await db.get(Member, member_id)
        if not member or member.deletedAt is not None or member.status != StatusType.ENABLE:
            await websocket.close(code=4401)
            return
        try:
            await assert_company_access(db, member, companyId)
        except Exception:
            await websocket.close(code=4403)
            return

    await websocket.accept()
    await incident_ws_hub.subscribe(companyId, websocket)
    last_check = time.monotonic()
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                pass
            if time.monotonic() - last_check >= 60.0:
                last_check = time.monotonic()
                try:
                    decode_token(token, expected_typ="access")
                    if await is_token_revoked(payload):
                        await websocket.close(code=4401)
                        return
                except Exception:
                    await websocket.close(code=4401)
                    return
    except WebSocketDisconnect:
        pass
    finally:
        await incident_ws_hub.unsubscribe(companyId, websocket)


@router.get("/company/{companyId}/dr/topology")
async def get_dr_topology(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.dr_replication_service import get_region_topology

    require_request_system_admin(request)
    return await get_region_topology(db)


@router.post("/dr/replicate")
async def receive_dr_replication(request: Request):
    import json
    from fastapi import HTTPException
    from ..services.dr_replication_service import (
        apply_incoming_replication_event,
        verify_replication_signature,
    )

    raw_body = await request.body()
    sig = request.headers.get("X-Sentinel-DR-Sig")
    if not verify_replication_signature(raw_body, sig):
        raise HTTPException(status_code=401, detail="Invalid DR replication signature")
    try:
        envelope = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed replication JSON") from None
    return await apply_incoming_replication_event(envelope)


# ============================================================================
# P3: Vehicle LPR & Smart Parking Management Endpoints
# ============================================================================


def _serialize_vehicle(v: Any) -> dict[str, Any]:
    return {
        "vehicleId": str(v.vehicleId),
        "companyId": str(v.companyId),
        "licensePlate": v.licensePlate,
        "province": v.province,
        "vehicleType": v.vehicleType,
        "brand": v.brand,
        "model": v.model,
        "color": v.color,
        "ownerType": v.ownerType,
        "ownerName": v.ownerName,
        "ownerContact": v.ownerContact,
        "companyEmployeeId": str(v.companyEmployeeId) if v.companyEmployeeId else None,
        "identityId": str(v.identityId) if v.identityId else None,
        "status": v.status,
        "notes": v.notes,
        "createdAt": v.createdAt.isoformat() if v.createdAt else None,
        "updatedAt": v.updatedAt.isoformat() if v.updatedAt else None,
    }


def _serialize_spot(s: Any) -> dict[str, Any]:
    return {
        "spotId": str(s.spotId),
        "companyId": str(s.companyId),
        "spotCode": s.spotCode,
        "zone": s.zone,
        "floor": s.floor,
        "spotType": s.spotType,
        "isOccupied": s.isOccupied,
        "occupiedVehicleId": str(s.occupiedVehicleId) if s.occupiedVehicleId else None,
        "occupiedPlate": s.occupiedPlate,
        "occupiedSince": s.occupiedSince.isoformat() if s.occupiedSince else None,
        "status": s.status,
        "createdAt": s.createdAt.isoformat() if s.createdAt else None,
        "updatedAt": s.updatedAt.isoformat() if s.updatedAt else None,
    }


def _serialize_parking_tx(tx: Any) -> dict[str, Any]:
    return {
        "transactionId": str(tx.transactionId),
        "companyId": str(tx.companyId),
        "vehicleId": str(tx.vehicleId) if tx.vehicleId else None,
        "spotId": str(tx.spotId) if tx.spotId else None,
        "licensePlate": tx.licensePlate,
        "province": tx.province,
        "entryTime": tx.entryTime.isoformat() if tx.entryTime else None,
        "exitTime": tx.exitTime.isoformat() if tx.exitTime else None,
        "dwellMinutes": tx.dwellMinutes,
        "gateIn": tx.gateIn,
        "gateOut": tx.gateOut,
        "entryConfidence": tx.entryConfidence,
        "exitConfidence": tx.exitConfidence,
        "entrySnapshotUrl": tx.entrySnapshotUrl,
        "exitSnapshotUrl": tx.exitSnapshotUrl,
        "authStatus": tx.authStatus,
        "actionTaken": tx.actionTaken,
        "createdAt": tx.createdAt.isoformat() if tx.createdAt else None,
    }


def _serialize_rfid_card(c: Any) -> dict[str, Any]:
    return {
        "cardId": str(c.cardId),
        "companyId": str(c.companyId),
        "cardNumber": c.cardNumber,
        "facilityCode": c.facilityCode,
        "cardType": c.cardType,
        "assignedType": c.assignedType,
        "companyEmployeeId": str(c.companyEmployeeId) if c.companyEmployeeId else None,
        "identityId": str(c.identityId) if c.identityId else None,
        "holderName": c.holderName,
        "cardStatus": c.cardStatus,
        "issuedAt": c.issuedAt.isoformat() if c.issuedAt else None,
        "expiresAt": c.expiresAt.isoformat() if c.expiresAt else None,
        "lastSwipedAt": c.lastSwipedAt.isoformat() if c.lastSwipedAt else None,
        "lastDoor": c.lastDoor,
        "notes": c.notes,
        "createdAt": c.createdAt.isoformat() if c.createdAt else None,
        "updatedAt": c.updatedAt.isoformat() if c.updatedAt else None,
    }


@router.get("/company/{companyId}/parking/overview")
async def get_parking_overview_endpoint(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import get_parking_overview

    await assert_request_company_access(request, db, companyId)
    return await get_parking_overview(db, companyId)


@router.get("/company/{companyId}/parking/spots")
async def get_parking_spots_endpoint(
    companyId: UUID,
    request: Request,
    zone: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    isOccupied: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import list_parking_spots

    await assert_request_company_access(request, db, companyId)
    spots = await list_parking_spots(db, companyId, zone=zone, status_filter=status, is_occupied=isOccupied)
    return [_serialize_spot(s) for s in spots]


@router.post("/company/{companyId}/parking/spots")
async def create_parking_spot_endpoint(
    companyId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import upsert_parking_spot

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    spot = await upsert_parking_spot(db, companyId, data)
    return _serialize_spot(spot)


@router.put("/company/{companyId}/parking/spots/{spotId}")
async def update_parking_spot_endpoint(
    companyId: UUID,
    spotId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import upsert_parking_spot

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    spot = await upsert_parking_spot(db, companyId, data, spot_id=spotId)
    return _serialize_spot(spot)


@router.delete("/company/{companyId}/parking/spots/{spotId}")
async def delete_parking_spot_endpoint(
    companyId: UUID,
    spotId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import delete_parking_spot

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    await delete_parking_spot(db, companyId, spotId)
    return {"success": True, "spotId": str(spotId)}


@router.get("/company/{companyId}/vehicles")
async def get_vehicles_endpoint(
    companyId: UUID,
    request: Request,
    query: Optional[str] = Query(None),
    ownerType: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import list_vehicles

    await assert_request_company_access(request, db, companyId)
    vehicles, total = await list_vehicles(
        db, companyId, query=query, owner_type=ownerType, status_filter=status, limit=limit, offset=offset
    )
    return {
        "items": [_serialize_vehicle(v) for v in vehicles],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/company/{companyId}/vehicles")
async def create_vehicle_endpoint(
    companyId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import create_or_update_vehicle

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    veh = await create_or_update_vehicle(db, companyId, data)
    return _serialize_vehicle(veh)


@router.put("/company/{companyId}/vehicles/{vehicleId}")
async def update_vehicle_endpoint(
    companyId: UUID,
    vehicleId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import create_or_update_vehicle

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    veh = await create_or_update_vehicle(db, companyId, data, vehicle_id=vehicleId)
    return _serialize_vehicle(veh)


@router.delete("/company/{companyId}/vehicles/{vehicleId}")
async def delete_vehicle_endpoint(
    companyId: UUID,
    vehicleId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import delete_vehicle

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    await delete_vehicle(db, companyId, vehicleId)
    return {"success": True, "vehicleId": str(vehicleId)}


@router.post("/company/{companyId}/parking/lpr-scan")
async def post_lpr_scan_endpoint(
    companyId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import lpr_barrier_scan

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await lpr_barrier_scan(db, companyId, data)


@router.get("/company/{companyId}/parking/transactions")
async def get_parking_transactions_endpoint(
    companyId: UUID,
    request: Request,
    licensePlate: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from ..services.parking_service import list_parking_transactions

    await assert_request_company_access(request, db, companyId)
    txs, total = await list_parking_transactions(
        db, companyId, license_plate=licensePlate, limit=limit, offset=offset
    )
    return {
        "items": [_serialize_parking_tx(tx) for tx in txs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ============================================================================
# P3: RFID Physical Access Card Management Endpoints
# ============================================================================


@router.get("/company/{companyId}/rfid-cards")
async def get_rfid_cards_endpoint(
    companyId: UUID,
    request: Request,
    query: Optional[str] = Query(None),
    cardStatus: Optional[str] = Query(None),
    assignedType: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from ..services.rfid_service import list_rfid_cards

    await assert_request_company_access(request, db, companyId)
    cards, total = await list_rfid_cards(
        db, companyId, query=query, card_status=cardStatus, assigned_type=assignedType, limit=limit, offset=offset
    )
    return {
        "items": [_serialize_rfid_card(c) for c in cards],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/company/{companyId}/rfid-cards")
async def create_rfid_card_endpoint(
    companyId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.rfid_service import issue_or_update_rfid_card

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    card = await issue_or_update_rfid_card(db, companyId, data)
    return _serialize_rfid_card(card)


@router.put("/company/{companyId}/rfid-cards/{cardId}")
async def update_rfid_card_endpoint(
    companyId: UUID,
    cardId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.rfid_service import issue_or_update_rfid_card

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    card = await issue_or_update_rfid_card(db, companyId, data, card_id=cardId)
    return _serialize_rfid_card(card)


@router.put("/company/{companyId}/rfid-cards/{cardId}/status")
async def update_rfid_card_status_endpoint(
    companyId: UUID,
    cardId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.rfid_service import update_rfid_card_status

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    new_status = data.get("cardStatus") or data.get("status") or "ACTIVE"
    notes = data.get("notes")
    card = await update_rfid_card_status(db, companyId, cardId, new_status, notes=notes)
    return _serialize_rfid_card(card)


@router.delete("/company/{companyId}/rfid-cards/{cardId}")
async def delete_rfid_card_endpoint(
    companyId: UUID,
    cardId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.rfid_service import delete_rfid_card

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    await delete_rfid_card(db, companyId, cardId)
    return {"success": True, "cardId": str(cardId)}


@router.post("/company/{companyId}/access/verify-rfid")
async def verify_rfid_access_endpoint(
    companyId: UUID,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    from ..services.rfid_service import verify_rfid_access

    await assert_request_permission(request, db, rbac_service.PERM_SENTINEL_MANAGE, companyId)
    return await verify_rfid_access(db, companyId, data)

