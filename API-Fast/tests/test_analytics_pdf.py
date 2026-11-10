"""Phase 6C PDF export — works with or without reportlab installed."""
from __future__ import annotations

from src.services.analytics_pdf_service import render_analytics_pdf


def test_render_analytics_pdf_minimal_header():
    pdf = render_analytics_pdf(
        {
            "start": "2026-11-01T00:00:00+00:00",
            "end": "2026-11-10T00:00:00+00:00",
            "timezone": "Asia/Bangkok",
            "kpis": {
                "totalEvents": 12,
                "peakOccupancy": 3,
                "avgDwellSeconds": 45.5,
                "camerasOnline": 2,
                "camerasOffline": 1,
                "camerasTotal": 3,
                "busySlots": [{"label": "Mon 09:00", "count": 5}],
            },
            "cameraHealth": {
                "summary": {"analysisEnabled": 1},
                "cameras": [
                    {
                        "name": "Lobby",
                        "health": "healthy",
                        "eventsInRange": 4,
                        "status": "online",
                    }
                ],
            },
            "dwell": {
                "cameras": [
                    {
                        "cameraName": "Lobby",
                        "avgDwellSeconds": 40,
                        "sessions": 2,
                        "totalDwellSeconds": 80,
                    }
                ]
            },
        }
    )
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 200


def test_resolve_range_caps_at_90_days():
    from datetime import datetime, timezone

    from src.services.analytics_service import resolve_range

    start, end = resolve_range(
        "2026-01-01T00:00:00+00:00",
        "2026-11-01T00:00:00+00:00",
    )
    assert end > start
    assert (end - start).days <= 90
    assert end.tzinfo is not None
    assert isinstance(start, datetime)
    assert start.tzinfo == timezone.utc or start.utcoffset() is not None
