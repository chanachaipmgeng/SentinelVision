"""SentinelVision HTTP routes (thin) — orchestration in controllers/services.

Stable re-exports for F3 / face_ws / worker / tests:
``evaluate_kiosk_sentinel_match``, ``evaluate_unified_scan_decision``,
``resolve_scan_zone``, ``maybe_dispatch_zone_relay``, ``expire_sentinel_identities_tick``,
and serializer / schedule helpers.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
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
    db: AsyncSession = Depends(get_db),
):
    """Company-scoped Security & HR AI Copilot (SSE stream)."""
    await assert_request_company_access(request, db, companyId)
    question = str((body or {}).get("question") or "").strip()
    history = (body or {}).get("history")
    if not isinstance(history, list):
        history = []
    return StreamingResponse(
        stream_assistant_chat(db, companyId, question, history),
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


@router.post("/company/{companyId}/zones/{zoneId}/evaluate-access")
async def evaluate_zone_access_route(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.evaluate_zone_access(db, companyId, zoneId, body)


@router.post("/company/{companyId}/zones/{zoneId}/edge-unlock")
async def edge_unlock_zone_route(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.edge_unlock_zone(db, companyId, zoneId, body)


@router.post("/company/{companyId}/health-check")
async def run_company_health_check_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await ctrl.run_company_health_check(db, companyId)


@router.post("/company/{companyId}/reindex-vectors")
async def reindex_company_vectors_route(
    companyId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
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
    await assert_request_company_access(request, db, companyId)
    return await ctrl.trigger_fire_alarm(db, companyId, body)


@router.post("/company/{companyId}/fire-alarm/reset")
async def reset_company_fire_alarm(
    companyId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
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


@router.post("/company/{companyId}/events/{eventId}/sessions/check-in")
async def checkin_event_breakout_session(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    from ..services.event_session_service import check_in_breakout_room

    await assert_request_company_access(request, db, companyId)
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


@router.get("/company/{companyId}/audit-verify")
async def verify_company_audit_chain(
    companyId: UUID,
    request: Request,
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    from ..services.audit_service import verify_audit_chain

    await assert_request_company_access(request, db, companyId)
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

    await assert_request_company_access(request, db, companyId)
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
    from ..services.visitor_invite_service import verify_visitor_invite_token

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
    return {"registered": True, "identity": created}


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
    from ..config.database import async_session
    from ..models.member import Member, StatusType
    from ..security.deps import assert_company_access
    from ..security.jwt import decode_token
    from ..services.incident_ws_hub import incident_ws_hub

    token = websocket.query_params.get("token") or websocket.cookies.get("dpu_access_token")
    if not token:
        auth_header = websocket.headers.get("authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_token(token)
        member_id = UUID(str(payload.get("sub")))
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
    try:
        while True:
            await websocket.receive_text()
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

    await assert_request_company_access(request, db, companyId)
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
