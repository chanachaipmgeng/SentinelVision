"""Local disk & S3/MinIO object storage service with AWS SigV4 presigned URLs and retention."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import logging
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from ..config.settings import settings

logger = logging.getLogger("dpu.storage")

ROOTS = {
    "uploaded_images": Path("uploaded_images"),
    "enrolled_images": Path("enrolled_images"),
    "temp_images": Path("temp_images"),
    "video_clips": Path("video_clips"),
}

# Evidence retention kinds (D4). Punch photos and incident snapshots must not share policy.
EVIDENCE_KIND_PUNCH_PHOTO = "punch_photo"
EVIDENCE_KIND_INCIDENT_SNAPSHOT = "incident_snapshot"
EVIDENCE_KIND_VIDEO_CLIP = "video_clip"
INCIDENT_SNAPSHOT_PREFIX = "incident_"
VIDEO_CLIP_PREFIX = "videoclip_"


def ensure_dirs() -> None:
    """Create the image / clip roots and make sure the (non-root) API user can write to them.

    Named volumes created by pre-B4 root containers stay root-owned; fail with the fix
    instead of surfacing as 500s on the first upload (docs/RUNBOOK.md "Upgrade to non-root").
    """
    import os

    not_writable: list[str] = []
    for path in ROOTS.values():
        path.mkdir(exist_ok=True)
        if not os.access(path, os.W_OK | os.X_OK):
            not_writable.append(str(path.resolve()))
    if not_writable:
        raise RuntimeError(
            "storage directories are not writable by uid %s: %s — chown the volumes once, e.g. "
            "`docker run --rm --volumes-from dpu-api alpine chown -R 10001:10001 %s`"
            % (os.getuid(), ", ".join(not_writable), " ".join(not_writable))
        )


def is_s3_enabled() -> bool:
    return (settings.STORAGE_BACKEND or "local").strip().lower() == "s3" and bool(
        (settings.S3_ENDPOINT_URL or "").strip() and (settings.S3_BUCKET or "").strip()
    )


def _s3_object_key(folder: str, filename: str) -> str:
    safe_folder = (folder or "uploaded_images").strip("/")
    safe_name = Path(filename).name
    return f"{safe_folder}/{safe_name}"


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret_key: str, date_stamp: str, region: str, service: str = "s3") -> bytes:
    k_date = _hmac_sha256(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    return _hmac_sha256(k_service, "aws4_request")


def generate_presigned_url(
    folder: str,
    filename: str,
    *,
    expires_seconds: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """
    Generate an AWS Signature V4 presigned GET URL for S3 / MinIO without requiring external SDKs.
    Returns None if S3 is not enabled or credentials are not configured.
    """
    if not is_s3_enabled():
        return None
    access_key = (settings.S3_ACCESS_KEY or "").strip()
    secret_key = (settings.S3_SECRET_KEY or "").strip()
    if not access_key or not secret_key:
        return None

    endpoint = (settings.S3_ENDPOINT_URL or "").strip().rstrip("/")
    bucket = (settings.S3_BUCKET or "dpu-attendance").strip().strip("/")
    region = (settings.S3_REGION or "ap-southeast-1").strip()
    ttl = max(60, min(604800, int(expires_seconds or settings.S3_PRESIGN_EXPIRES_SECONDS or 3600)))

    dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    amz_date = dt.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = dt.strftime("%Y%m%d")

    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    base_path = parsed.path.rstrip("/")
    obj_key = _s3_object_key(folder, filename)
    canonical_uri = f"{base_path}/{bucket}/{ urllib.parse.quote(obj_key, safe='/~_.-') }"
    if not canonical_uri.startswith("/"):
        canonical_uri = "/" + canonical_uri

    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    query_params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{access_key}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(ttl),
        "X-Amz-SignedHeaders": "host",
    }
    canonical_querystring = "&".join(
        f"{urllib.parse.quote(k, safe='~_.-')}={urllib.parse.quote(v, safe='~_.-')}"
        for k, v in sorted(query_params.items())
    )
    canonical_headers = f"host:{host}\n"
    signed_headers = "host"
    payload_hash = "UNSIGNED-PAYLOAD"

    canonical_request = "\n".join(
        [
            "GET",
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    sig_key = _signing_key(secret_key, date_stamp, region, "s3")
    signature = hmac.new(sig_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"{parsed.scheme}://{host}{canonical_uri}?{canonical_querystring}&X-Amz-Signature={signature}"


def _s3_request(
    method: str,
    folder: str,
    filename: str,
    *,
    body: bytes = b"",
    content_type: str = "application/octet-stream",
) -> tuple[int, bytes]:
    endpoint = (settings.S3_ENDPOINT_URL or "").strip().rstrip("/")
    bucket = (settings.S3_BUCKET or "dpu-attendance").strip().strip("/")
    region = (settings.S3_REGION or "ap-southeast-1").strip()
    access_key = (settings.S3_ACCESS_KEY or "").strip()
    secret_key = (settings.S3_SECRET_KEY or "").strip()

    dt = datetime.now(timezone.utc)
    amz_date = dt.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = dt.strftime("%Y%m%d")

    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    base_path = parsed.path.rstrip("/")
    obj_key = _s3_object_key(folder, filename)
    canonical_uri = f"{base_path}/{bucket}/{urllib.parse.quote(obj_key, safe='/~_.-')}"
    if not canonical_uri.startswith("/"):
        canonical_uri = "/" + canonical_uri

    payload_hash = hashlib.sha256(body).hexdigest()
    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            method.upper(),
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    sig_key = _signing_key(secret_key, date_stamp, region, "s3")
    signature = hmac.new(sig_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    auth_header = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"{parsed.scheme}://{host}{canonical_uri}"
    headers = {
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": auth_header,
    }
    if method.upper() == "PUT":
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(body))

    req = urllib.request.Request(
        url,
        data=body if method.upper() in ("PUT", "POST") else None,
        headers=headers,
        method=method.upper(),
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return int(resp.status), resp.read()


def store_image_bytes(
    folder: str,
    filename: str,
    content: bytes,
    *,
    content_type: str = "image/jpeg",
) -> str:
    """Save image bytes to local storage and (when STORAGE_BACKEND=s3) upload to S3/MinIO."""
    ensure_dirs()
    root = ROOTS.get(folder, Path(folder))
    root.mkdir(exist_ok=True)
    safe_name = Path(filename).name
    local_path = root / safe_name
    local_path.write_bytes(content)

    if is_s3_enabled():
        try:
            _s3_request("PUT", folder, safe_name, body=content, content_type=content_type)
        except Exception as exc:
            logger.warning("S3 upload failed for %s/%s (kept local copy): %s", folder, safe_name, exc)
    return safe_name


def store_image_file(
    folder: str,
    filename: str,
    source_path: str | Path,
    *,
    move: bool = False,
    content_type: str = "image/jpeg",
) -> str:
    """Copy or move a local file into managed storage and upload to S3/MinIO when enabled."""
    ensure_dirs()
    root = ROOTS.get(folder, Path(folder))
    root.mkdir(exist_ok=True)
    safe_name = Path(filename).name
    dest_path = root / safe_name
    src = Path(source_path)
    if move:
        shutil.move(str(src), str(dest_path))
    else:
        shutil.copyfile(str(src), str(dest_path))

    if is_s3_enabled():
        try:
            content = dest_path.read_bytes()
            _s3_request("PUT", folder, safe_name, body=content, content_type=content_type)
        except Exception as exc:
            logger.warning("S3 upload failed for %s/%s (kept local copy): %s", folder, safe_name, exc)
    return safe_name


def read_image_bytes(folder: str, filename: str) -> Optional[bytes]:
    """Read image bytes from local cache first, falling back to S3/MinIO when enabled."""
    root = ROOTS.get(folder, Path(folder))
    safe_name = Path(filename).name
    local_path = root / safe_name
    if local_path.is_file():
        return local_path.read_bytes()
    if is_s3_enabled():
        try:
            status_code, data = _s3_request("GET", folder, safe_name)
            if 200 <= status_code < 300 and data:
                root.mkdir(exist_ok=True)
                local_path.write_bytes(data)
                return data
        except Exception as exc:
            logger.warning("S3 GET failed for %s/%s: %s", folder, safe_name, exc)
    return None


def delete_stored_image(folder: str, filename: str) -> bool:
    """Delete an image from both local disk and S3/MinIO (used by PDPA Right to Erasure)."""
    removed = False
    root = ROOTS.get(folder, Path(folder))
    safe_name = Path(filename).name
    local_path = root / safe_name
    if local_path.exists():
        try:
            local_path.unlink()
            removed = True
        except OSError:
            pass
    if is_s3_enabled():
        try:
            _s3_request("DELETE", folder, safe_name)
            removed = True
        except Exception as exc:
            logger.warning("S3 DELETE failed for %s/%s: %s", folder, safe_name, exc)
    return removed


def purge_older_than(
    folder: str,
    max_age_seconds: int,
    *,
    exclude_prefixes: tuple[str, ...] = (),
    include_prefixes: tuple[str, ...] | None = None,
) -> int:
    root = ROOTS[folder]
    if not root.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for path in root.iterdir():
        try:
            if not path.is_file() or path.stat().st_mtime >= cutoff:
                continue
            name = path.name
            if exclude_prefixes and name.startswith(exclude_prefixes):
                continue
            if include_prefixes is not None and not name.startswith(include_prefixes):
                continue
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def store_evidence_image(
    kind: str,
    filename: str,
    source_path: str | Path,
    *,
    move: bool = False,
    content_type: str = "image/jpeg",
) -> str:
    """Store evidence under a retention kind. Incident snapshots keep a distinct prefix
    so global punch-photo retention never deletes them (D4 ``incidentSnapshotDays`` owns them).
    Video clips live in ``video_clips/`` and never share punch-photo retention.
    """
    safe_name = Path(filename).name
    if kind == EVIDENCE_KIND_VIDEO_CLIP:
        if not safe_name.startswith(VIDEO_CLIP_PREFIX):
            safe_name = f"{VIDEO_CLIP_PREFIX}{safe_name}"
        return store_image_file(
            "video_clips",
            safe_name,
            source_path,
            move=move,
            content_type=content_type or "video/mp4",
        )
    if kind == EVIDENCE_KIND_INCIDENT_SNAPSHOT:
        if not safe_name.startswith(INCIDENT_SNAPSHOT_PREFIX):
            safe_name = f"{INCIDENT_SNAPSHOT_PREFIX}{safe_name}"
        return store_image_file(
            "uploaded_images", safe_name, source_path, move=move, content_type=content_type
        )
    # Default / punch_photo
    return store_image_file(
        "uploaded_images", safe_name, source_path, move=move, content_type=content_type
    )


def store_evidence_bytes(
    kind: str,
    filename: str,
    content: bytes,
    *,
    content_type: str = "application/octet-stream",
) -> str:
    """Byte-oriented evidence store (used by video clip export)."""
    safe_name = Path(filename).name
    if kind == EVIDENCE_KIND_VIDEO_CLIP:
        if not safe_name.startswith(VIDEO_CLIP_PREFIX):
            safe_name = f"{VIDEO_CLIP_PREFIX}{safe_name}"
        return store_image_bytes(
            "video_clips", safe_name, content, content_type=content_type or "video/mp4"
        )
    if kind == EVIDENCE_KIND_INCIDENT_SNAPSHOT:
        if not safe_name.startswith(INCIDENT_SNAPSHOT_PREFIX):
            safe_name = f"{INCIDENT_SNAPSHOT_PREFIX}{safe_name}"
        return store_image_bytes("uploaded_images", safe_name, content, content_type=content_type)
    return store_image_bytes("uploaded_images", safe_name, content, content_type=content_type)


def retention_tick() -> dict:
    backend = (settings.STORAGE_BACKEND or "local").strip().lower()
    if backend not in {"local", "s3"}:
        raise RuntimeError(f"Unknown STORAGE_BACKEND {settings.STORAGE_BACKEND}")
    temp = purge_older_than("temp_images", int(settings.TEMP_RETENTION_HOURS) * 3600)
    # Punch photos only — never share policy with incident_snapshot evidence.
    punches = purge_older_than(
        "uploaded_images",
        int(settings.IMAGE_RETENTION_DAYS) * 86400,
        exclude_prefixes=(INCIDENT_SNAPSHOT_PREFIX,),
    )
    # Global fallback for orphaned incident_* files (primary path is PDPA company_retention_tick).
    incident_days = int(
        getattr(settings, "INCIDENT_SNAPSHOT_RETENTION_DAYS", None)
        or getattr(settings, "IMAGE_RETENTION_DAYS", 90)
        or 90
    )
    incidents = 0
    if incident_days > 0:
        incidents = purge_older_than(
            "uploaded_images",
            incident_days * 86400,
            include_prefixes=(INCIDENT_SNAPSHOT_PREFIX,),
        )
    clip_days = int(
        getattr(settings, "VIDEO_CLIP_RETENTION_DAYS", None)
        or getattr(settings, "IMAGE_RETENTION_DAYS", 90)
        or 90
    )
    clips = 0
    if clip_days > 0:
        clips = purge_older_than("video_clips", clip_days * 86400)
    return {
        "backend": backend,
        "s3Configured": is_s3_enabled(),
        "s3Bucket": settings.S3_BUCKET if is_s3_enabled() else None,
        "tempRemoved": temp,
        "uploadsRemoved": punches,
        "incidentSnapshotsRemoved": incidents,
        "videoClipsRemoved": clips,
        "evidenceKinds": {
            EVIDENCE_KIND_PUNCH_PHOTO: "uploaded_images (non-incident_*)",
            EVIDENCE_KIND_INCIDENT_SNAPSHOT: f"uploaded_images ({INCIDENT_SNAPSHOT_PREFIX}*)",
            EVIDENCE_KIND_VIDEO_CLIP: f"video_clips ({VIDEO_CLIP_PREFIX}*)",
        },
    }


def get_storage_status() -> dict:
    ensure_dirs()
    counts = {}
    for name, root in ROOTS.items():
        try:
            counts[name] = sum(1 for p in root.iterdir() if p.is_file()) if root.exists() else 0
        except OSError:
            counts[name] = 0
    return {
        "backend": (settings.STORAGE_BACKEND or "local").strip().lower(),
        "s3Enabled": is_s3_enabled(),
        "s3Endpoint": settings.S3_ENDPOINT_URL or None,
        "s3Bucket": settings.S3_BUCKET or None,
        "s3Region": settings.S3_REGION or "ap-southeast-1",
        "presignExpiresSeconds": int(settings.S3_PRESIGN_EXPIRES_SECONDS or 3600),
        "imageRetentionDays": int(settings.IMAGE_RETENTION_DAYS),
        "tempRetentionHours": int(settings.TEMP_RETENTION_HOURS),
        "localFileCounts": counts,
    }
