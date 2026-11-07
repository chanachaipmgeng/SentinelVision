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
}


def ensure_dirs() -> None:
    for path in ROOTS.values():
        path.mkdir(exist_ok=True)


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


def purge_older_than(folder: str, max_age_seconds: int) -> int:
    root = ROOTS[folder]
    if not root.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for path in root.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def retention_tick() -> dict:
    backend = (settings.STORAGE_BACKEND or "local").strip().lower()
    if backend not in {"local", "s3"}:
        raise RuntimeError(f"Unknown STORAGE_BACKEND {settings.STORAGE_BACKEND}")
    temp = purge_older_than("temp_images", int(settings.TEMP_RETENTION_HOURS) * 3600)
    punches = purge_older_than("uploaded_images", int(settings.IMAGE_RETENTION_DAYS) * 86400)
    return {
        "backend": backend,
        "s3Configured": is_s3_enabled(),
        "s3Bucket": settings.S3_BUCKET if is_s3_enabled() else None,
        "tempRemoved": temp,
        "uploadsRemoved": punches,
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
