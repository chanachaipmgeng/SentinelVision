"""Pure-Python ONVIF WS-Discovery & PTZ SOAP control (no native C extensions)."""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any
from urllib.parse import unquote, urlparse
import uuid
import xml.etree.ElementTree as ET

from fastapi import HTTPException, status
import httpx

from ..models.camera import Camera

logger = logging.getLogger("dpu.onvif")

WS_DISCOVERY_MULTICAST = "239.255.255.250"
WS_DISCOVERY_PORT = 3702
_ALLOWED_PTZ_ACTIONS = {"move", "stop"}


def build_ws_discovery_probe(message_id: str | None = None) -> bytes:
    mid = message_id or f"uuid:{uuid.uuid4()}"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
        'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
        'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
        'xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
        "<e:Header>"
        f"<w:MessageID>{mid}</w:MessageID>"
        "<w:To e:mustUnderstand=\"true\">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>"
        "<w:Action e:mustUnderstand=\"true\">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>"
        "</e:Header>"
        "<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>"
        "</e:Envelope>"
    )
    return xml.encode("utf-8")


def parse_ws_discovery_response(raw_xml: bytes, source_ip: str) -> dict[str, Any] | None:
    """Parse a single WS-Discovery ProbeMatch XML datagram into a camera candidate."""
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return None

    xaddrs_text = ""
    scopes_text = ""
    epr_text = ""
    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower()
        if tag == "xaddrs" and elem.text:
            xaddrs_text = elem.text.strip()
        elif tag == "scopes" and elem.text:
            scopes_text = elem.text.strip()
        elif tag == "address" and elem.text and not epr_text:
            epr_text = elem.text.strip()

    if not xaddrs_text:
        return None

    xaddrs = [u for u in xaddrs_text.split() if u.startswith("http")]
    if not xaddrs:
        return None

    name = ""
    hardware = ""
    for scope in scopes_text.split():
        if "/name/" in scope:
            name = unquote(scope.split("/name/", 1)[1])
        elif "/hardware/" in scope:
            hardware = unquote(scope.split("/hardware/", 1)[1])

    parsed = urlparse(xaddrs[0])
    return {
        "endpointReference": epr_text or None,
        "ip": parsed.hostname or source_ip,
        "onvifServiceUrl": xaddrs[0],
        "xaddrs": xaddrs,
        "name": name or f"ONVIF Camera ({parsed.hostname or source_ip})",
        "hardware": hardware or None,
    }


def _discover_sync(timeout_seconds: float) -> list[dict[str, Any]]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(max(0.2, min(float(timeout_seconds), 5.0)))
    found: dict[str, dict[str, Any]] = {}
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(build_ws_discovery_probe(), (WS_DISCOVERY_MULTICAST, WS_DISCOVERY_PORT))
        deadline = asyncio.get_event_loop().time() + timeout_seconds if False else None
        _ = deadline
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            parsed = parse_ws_discovery_response(data, addr[0])
            if parsed:
                found[parsed["onvifServiceUrl"]] = parsed
    except OSError as exc:
        logger.debug("ONVIF WS-Discovery socket error: %s", exc)
    finally:
        sock.close()
    return list(found.values())


async def discover_onvif_devices(timeout_seconds: float = 2.0) -> list[dict[str, Any]]:
    """Run non-blocking ONVIF WS-Discovery probe on the local LAN."""
    bounded = max(0.3, min(float(timeout_seconds), 5.0))
    return await asyncio.to_thread(_discover_sync, bounded)


def _resolve_ptz_endpoint(camera: Camera, override_url: str | None = None) -> str:
    from ..security.ssrf import validate_outbound_url

    candidate = (override_url or "").strip()
    if not candidate:
        parsed = urlparse(camera.streamUrl or "")
        if not parsed.hostname:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Camera has no valid host for ONVIF PTZ",
            )
        candidate = f"http://{parsed.hostname}/onvif/ptz_service"

    return validate_outbound_url(candidate, allow_private_lan=True)


def build_ptz_soap_envelope(
    *,
    action: str,
    profile_token: str = "Profile_1",
    pan: float = 0.0,
    tilt: float = 0.0,
    zoom: float = 0.0,
) -> str:
    act = action.strip().lower()
    if act not in _ALLOWED_PTZ_ACTIONS:
        raise HTTPException(status_code=400, detail="PTZ action must be 'move' or 'stop'")
    safe_token = "".join(c for c in profile_token if c.isalnum() or c in {"_", "-"}) or "Profile_1"
    if act == "stop":
        body = (
            "<tptz:Stop>"
            f"<tptz:ProfileToken>{safe_token}</tptz:ProfileToken>"
            "<tptz:PanTilt>true</tptz:PanTilt>"
            "<tptz:Zoom>true</tptz:Zoom>"
            "</tptz:Stop>"
        )
    else:
        px = max(-1.0, min(1.0, float(pan)))
        py = max(-1.0, min(1.0, float(tilt)))
        zx = max(-1.0, min(1.0, float(zoom)))
        body = (
            "<tptz:ContinuousMove>"
            f"<tptz:ProfileToken>{safe_token}</tptz:ProfileToken>"
            "<tptz:Velocity>"
            f'<tt:PanTilt x="{px:.3f}" y="{py:.3f}"/>'
            f'<tt:Zoom x="{zx:.3f}"/>'
            "</tptz:Velocity>"
            "</tptz:ContinuousMove>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
        'xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl" '
        'xmlns:tt="http://www.onvif.org/ver10/schema">'
        f"<s:Body>{body}</s:Body>"
        "</s:Envelope>"
    )


async def send_ptz_command(
    camera: Camera,
    *,
    action: str,
    profile_token: str = "Profile_1",
    pan: float = 0.0,
    tilt: float = 0.0,
    zoom: float = 0.0,
    onvif_url: str | None = None,
) -> dict[str, Any]:
    endpoint = _resolve_ptz_endpoint(camera, onvif_url)
    envelope = build_ptz_soap_envelope(
        action=action,
        profile_token=profile_token,
        pan=pan,
        tilt=tilt,
        zoom=zoom,
    )
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
        resp = await client.post(
            endpoint,
            content=envelope.encode("utf-8"),
            headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        )
    return {
        "cameraId": str(camera.cameraId),
        "endpoint": endpoint,
        "action": action.strip().lower(),
        "statusCode": resp.status_code,
        "ok": 200 <= resp.status_code < 300,
    }
