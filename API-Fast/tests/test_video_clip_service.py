"""Unit tests for Phase 4B video clip helpers (no MediaMTX / ffmpeg required)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.models.video_clip import CLIP_KIND_EVENT, VideoClip
from src.services import storage_service, video_clip_service


def test_parse_segment_start_mediamtx_name():
    dt = video_clip_service._parse_segment_start("2026-11-09_19-30-00-123456.mp4")
    assert dt is not None
    assert dt == datetime(2026, 11, 9, 19, 30, 0, 123456, tzinfo=timezone.utc)


def test_serialize_clip_includes_download_path():
    company_id = uuid4()
    clip = VideoClip(
        clipId=uuid4(),
        companyId=company_id,
        cameraId=uuid4(),
        incidentId=None,
        startedAt=datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc),
        endedAt=datetime(2026, 11, 9, 12, 0, 15, tzinfo=timezone.utc),
        storageKey="videoclip_abc.mp4",
        durationMs=15000,
        kind=CLIP_KIND_EVENT,
    )
    data = video_clip_service.serialize_clip(clip, camera_name="Gate A")
    assert data["cameraName"] == "Gate A"
    assert data["kind"] == "event"
    assert data["durationMs"] == 15000
    assert data["downloadPath"].endswith(f"/clips/{clip.clipId}/download")


def test_video_clip_retention_kind_isolated_from_punch_photos(tmp_path, monkeypatch):
    monkeypatch.setitem(storage_service.ROOTS, "video_clips", tmp_path / "video_clips")
    monkeypatch.setitem(storage_service.ROOTS, "uploaded_images", tmp_path / "uploaded_images")
    monkeypatch.setitem(storage_service.ROOTS, "temp_images", tmp_path / "temp_images")
    (tmp_path / "video_clips").mkdir()
    (tmp_path / "uploaded_images").mkdir()
    (tmp_path / "temp_images").mkdir()

    src = tmp_path / "src.mp4"
    src.write_bytes(b"fake-mp4")
    stored = storage_service.store_evidence_image(
        storage_service.EVIDENCE_KIND_VIDEO_CLIP,
        "demo.mp4",
        src,
        content_type="video/mp4",
    )
    assert stored.startswith(storage_service.VIDEO_CLIP_PREFIX)
    assert (tmp_path / "video_clips" / stored).is_file()
    # Must not land in punch-photo folder
    assert not (tmp_path / "uploaded_images" / stored).exists()

    from src.config.settings import settings

    monkeypatch.setattr(settings, "VIDEO_CLIP_RETENTION_DAYS", 1)
    monkeypatch.setattr(settings, "IMAGE_RETENTION_DAYS", 90)
    monkeypatch.setattr(settings, "TEMP_RETENTION_HOURS", 24)
    # Age the clip file
    aged = tmp_path / "video_clips" / stored
    import os

    os.utime(aged, (0, 0))
    punch = tmp_path / "uploaded_images" / "punch.jpg"
    punch.write_bytes(b"jpg")
    result = storage_service.retention_tick()
    assert result["videoClipsRemoved"] >= 1
    assert not aged.exists()
    assert punch.exists()


def test_pre_post_defaults():
    assert video_clip_service.pre_seconds() >= 0
    assert video_clip_service.post_seconds() >= 0
