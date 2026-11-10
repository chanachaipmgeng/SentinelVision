"""Phase 6C — PDF export for face-monitor analytics summary.

Uses reportlab when available; otherwise falls back to a minimal PDF writer
so Docker images without the optional dep still return a valid PDF.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any


def _escape_pdf_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _minimal_pdf(lines: list[str]) -> bytes:
    """Tiny PDF 1.4 writer (Helvetica) — no external deps."""
    y = 780
    content_parts = ["BT /F1 11 Tf 50 800 Td 14 TL"]
    for i, line in enumerate(lines):
        safe = _escape_pdf_text(line[:110])
        if i == 0:
            content_parts.append(f"({safe}) Tj")
        else:
            content_parts.append(f"T* ({safe}) Tj")
        y -= 14
        if y < 50:
            break
    content_parts.append("ET")
    stream = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("ascii")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))
    out.write(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return out.getvalue()


def _build_lines(summary: dict[str, Any]) -> list[str]:
    kpis = summary.get("kpis") or {}
    health = (summary.get("cameraHealth") or {}).get("summary") or {}
    busy = kpis.get("busySlots") or []
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "SentinelVision — Face Monitor Analytics",
        f"Generated: {generated}",
        f"Range: {summary.get('start', '')} → {summary.get('end', '')}",
        f"Timezone: {summary.get('timezone', 'Asia/Bangkok')}",
        "",
        "Key metrics",
        f"  Total events: {kpis.get('totalEvents', 0)}",
        f"  Peak occupancy: {kpis.get('peakOccupancy', 0)}",
        f"  Avg dwell (s): {kpis.get('avgDwellSeconds', 0)}",
        f"  Cameras: {kpis.get('camerasOnline', 0)} online / "
        f"{kpis.get('camerasOffline', 0)} offline / {kpis.get('camerasTotal', 0)} total",
        f"  Analysis enabled: {health.get('analysisEnabled', 0)}",
        "",
        "Busiest hour x weekday slots",
    ]
    if not busy:
        lines.append("  (no events in range)")
    for slot in busy:
        lines.append(f"  - {slot.get('label')}: {slot.get('count')} events")

    lines.append("")
    lines.append("Camera health")
    for cam in (summary.get("cameraHealth") or {}).get("cameras") or []:
        lines.append(
            f"  - {cam.get('name')}: {cam.get('health')} "
            f"(events={cam.get('eventsInRange', 0)}, status={cam.get('status')})"
        )

    lines.append("")
    lines.append("Dwell by camera/zone")
    for d in (summary.get("dwell") or {}).get("cameras") or []:
        label = d.get("cameraName") or d.get("zoneName") or d.get("cameraId") or "unknown"
        lines.append(
            f"  - {label}: avg={d.get('avgDwellSeconds')}s "
            f"sessions={d.get('sessions')} total={d.get('totalDwellSeconds')}s"
        )
    return lines


def render_analytics_pdf(summary: dict[str, Any]) -> bytes:
    """Return PDF bytes for the analytics summary bundle."""
    lines = _build_lines(summary)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return _minimal_pdf(lines)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 48
    c.setTitle("SentinelVision Face Monitor Analytics")
    for i, line in enumerate(lines):
        if y < 48:
            c.showPage()
            y = height - 48
        font_size = 14 if i == 0 else 10
        c.setFont("Helvetica-Bold" if i == 0 or line in (
            "Key metrics",
            "Busiest hour x weekday slots",
            "Camera health",
            "Dwell by camera/zone",
        ) else "Helvetica", font_size)
        c.drawString(48, y, line[:110])
        y -= 16 if i == 0 else 13
    c.save()
    return buf.getvalue()
