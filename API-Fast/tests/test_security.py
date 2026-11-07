from datetime import datetime, timezone
import numpy as np
from src.security.passwords import generate_temp_password
from src.security.totp import (
    generate_totp_secret,
    generate_totp_code,
    verify_totp,
    build_otpauth_uri,
)
from src.security.jwt import (
    create_kiosk_token,
    decode_token,
    hash_kiosk_token,
)
from src.utils.liveness_detection import check_passive_antispoof_bgr
from src.controllers.employee_timestamp_controller import (
    _compute_shift_metrics,
    get_bangkok_tz,
)
from src.services.notification_service import (
    compute_webhook_signature,
    verify_webhook_signature,
)
from src.services.storage_service import generate_presigned_url
from src.services.observability import (
    get_observability_summary,
    observe_histogram,
    parse_or_create_traceparent,
    render_metrics,
)


def test_temp_password_is_not_1234():
    password = generate_temp_password()
    assert password != "1234"
    assert len(password) >= 8


def test_secret_rejects_default(monkeypatch):
    import src.config.settings as settings_mod
    from src.security.jwt import assert_secret_configured

    monkeypatch.setattr(settings_mod.settings, "AUTH_FAIL_FAST", True)
    monkeypatch.setattr(settings_mod.settings, "SECRET_KEY", "change-me-in-production")
    try:
        assert_secret_configured()
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_shift_metrics_late_and_overtime():
    tz = get_bangkok_tz()
    shift_cfg = {
        "name": "Standard Shift",
        "startTime": "09:00",
        "endTime": "18:00",
        "graceMinutes": 15,
    }
    # 09:10 Bangkok time (within 15m grace -> not late)
    ts_on_time = datetime(2026, 11, 7, 9, 10, 0, tzinfo=tz)
    is_late, late_min, ot_min, s_name = _compute_shift_metrics(
        ts_on_time, shift_cfg, is_checkout=False
    )
    assert is_late is False
    assert late_min == 0
    assert ot_min == 0
    assert s_name == "Standard Shift"

    # 09:25 Bangkok time (25 mins after 09:00 -> late 25 mins)
    ts_late = datetime(2026, 11, 7, 9, 25, 0, tzinfo=tz)
    is_late2, late_min2, ot_min2, _ = _compute_shift_metrics(
        ts_late, shift_cfg, is_checkout=False
    )
    assert is_late2 is True
    assert late_min2 == 25
    assert ot_min2 == 0

    # 19:00 Bangkok time (60 mins after 18:00 -> OT 60 mins)
    ts_checkout_ot = datetime(2026, 11, 7, 19, 0, 0, tzinfo=tz)
    is_late3, late_min3, ot_min3, _ = _compute_shift_metrics(
        ts_checkout_ot, shift_cfg, is_checkout=True
    )
    assert is_late3 is False
    assert late_min3 == 0
    assert ot_min3 == 60


def test_cross_midnight_shift_metrics():
    tz = get_bangkok_tz()
    night_shift = {
        "name": "Night Shift",
        "startTime": "22:00",
        "endTime": "06:00",
        "graceMinutes": 15,
        "isCrossMidnight": True,
    }
    # Check-in at 22:10 -> within 15m grace -> not late
    ts_in_ok = datetime(2026, 11, 7, 22, 10, 0, tzinfo=tz)
    is_late1, late_min1, ot_min1, s_name = _compute_shift_metrics(
        ts_in_ok, night_shift, is_checkout=False
    )
    assert is_late1 is False
    assert late_min1 == 0
    assert s_name == "Night Shift"

    # Check-in after midnight at 00:30 -> 150 mins after 22:00 yesterday -> late 150 mins
    ts_in_after_midnight = datetime(2026, 11, 8, 0, 30, 0, tzinfo=tz)
    is_late2, late_min2, _, _ = _compute_shift_metrics(
        ts_in_after_midnight, night_shift, is_checkout=False
    )
    assert is_late2 is True
    assert late_min2 == 150

    # Check-out next morning at 07:15 -> 75 mins after 06:00 -> OT 75 mins
    ts_out_ot = datetime(2026, 11, 8, 7, 15, 0, tzinfo=tz)
    is_late3, late_min3, ot_min3, _ = _compute_shift_metrics(
        ts_out_ot, night_shift, is_checkout=True
    )
    assert is_late3 is False
    assert late_min3 == 0
    assert ot_min3 == 75


def test_totp_generation_and_verification():
    secret = generate_totp_secret()
    assert len(secret) >= 16
    now_ts = 1700000000
    code = generate_totp_code(secret, timestamp=now_ts)
    assert len(code) == 6
    assert code.isdigit()
    assert verify_totp(secret, code, timestamp=now_ts) is True
    # Adjacent 30s window is still accepted
    assert verify_totp(secret, code, timestamp=now_ts + 25) is True
    # Far future window is rejected
    assert verify_totp(secret, code, timestamp=now_ts + 300) is False
    assert verify_totp(secret, "000000", timestamp=now_ts) is False
    uri = build_otpauth_uri(secret, "admin@dpu.local")
    assert uri.startswith("otpauth://totp/")
    assert f"secret={secret}" in uri


def test_kiosk_token_scope():
    token = create_kiosk_token(
        device_id="dev-123",
        company_id="comp-456",
        location_id="loc-789",
        expires_days=30,
    )
    payload = decode_token(token, expected_typ="kiosk")
    assert payload["typ"] == "kiosk"
    assert payload["deviceId"] == "dev-123"
    assert payload["companyId"] == "comp-456"
    assert payload["locationId"] == "loc-789"
    assert len(hash_kiosk_token(token)) == 64


def test_passive_antispoof_rejects_flat_and_glare():
    # 1. Flat grayscale image -> 0 chrominance variance -> rejected
    flat_gray = np.full((64, 64, 3), 120, dtype=np.uint8)
    ok_gray, msg_gray = check_passive_antispoof_bgr(flat_gray)
    assert ok_gray is False
    assert "chrominance" in msg_gray.lower()

    # 2. Natural varied skin-tone chrominance image -> passes
    natural = np.zeros((64, 64, 3), dtype=np.uint8)
    for r in range(64):
        for c in range(64):
            natural[r, c] = [
                110 + (r % 30),       # B
                135 + (c % 35),       # G
                175 + ((r + c) % 45), # R
            ]
    ok_nat, msg_nat = check_passive_antispoof_bgr(natural)
    assert ok_nat is True

    # 3. Screen glare / specular reflection (> 22% pure white pixels on top of natural region)
    glare_img = natural.copy()
    glare_img[:32, :, :] = 255  # 50% pure white screen glare
    ok_glare, msg_glare = check_passive_antispoof_bgr(glare_img)
    assert ok_glare is False
    assert "glare" in msg_glare.lower()


def test_webhook_hmac_sha256_signature():
    secret = "whsec_enterprise_payroll_secret_key"
    ts_str = "1700000000"
    body = b'{"event":"attendance.checked_in","employeeId":"EMP-001"}'
    sig = compute_webhook_signature(secret, ts_str, body)
    assert sig.startswith("v1=")
    assert len(sig) == 67

    # Valid signature & within timestamp window -> True
    assert verify_webhook_signature(secret, ts_str, body, sig, now_ts=1700000050) is True
    # Tampered body -> False
    assert verify_webhook_signature(secret, ts_str, b'{"tampered":true}', sig, now_ts=1700000050) is False
    # Replay attack outside 300s window -> False
    assert verify_webhook_signature(secret, ts_str, body, sig, now_ts=1700001000) is False


def test_s3_presigned_url_generation(monkeypatch):
    import src.config.settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings_mod.settings, "S3_ENDPOINT_URL", "https://s3.ap-southeast-1.amazonaws.com")
    monkeypatch.setattr(settings_mod.settings, "S3_BUCKET", "dpu-attendance-prod")
    monkeypatch.setattr(settings_mod.settings, "S3_REGION", "ap-southeast-1")
    monkeypatch.setattr(settings_mod.settings, "S3_ACCESS_KEY", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setattr(settings_mod.settings, "S3_SECRET_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    fixed_now = datetime(2026, 11, 7, 9, 0, 0, tzinfo=timezone.utc)
    url = generate_presigned_url(
        "enrolled_images",
        "face-123.jpg",
        expires_seconds=900,
        now=fixed_now,
    )
    assert url is not None
    assert url.startswith("https://s3.ap-southeast-1.amazonaws.com/dpu-attendance-prod/enrolled_images/face-123.jpg?")
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url
    assert "X-Amz-Expires=900" in url
    assert "X-Amz-Signature=" in url


def test_observability_histograms_and_traceparent():
    incoming_tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    trace_id, span_id, out_tp = parse_or_create_traceparent(incoming_tp)
    assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert len(span_id) == 16
    assert out_tp.startswith(f"00-{trace_id}-")

    observe_histogram("dpu_face_gpu_latency_ms", 18.5)
    observe_histogram("dpu_pgvector_search_ms", 4.2)
    prom_text = render_metrics()
    # Legacy millisecond names map onto the prometheus_client base-unit series (B6).
    assert 'dpu_face_gpu_processing_seconds_bucket{kind="other",le="0.025"}' in prom_text
    assert 'dpu_face_match_duration_seconds_count{source="pgvector"}' in prom_text

    summary = get_observability_summary()
    assert summary["histograms"]["dpu_face_gpu_latency_ms"]["count"] >= 1
    assert summary["histograms"]["dpu_pgvector_search_ms"]["count"] >= 1
