#!/usr/bin/env python3
"""Load-test the face kiosk WebSocket (/face/ws/kiosk) from the host.

Simulates N concurrent kiosk screens: JWT session, detect at ~90 ms,
optional identify / check-in under the same concurrency caps as the UI.
Use --faces-per-kiosk to mosaic multiple faces into each detect frame and
drive up to 2 identify / 3 check-in in flight per screen (UI caps).

Credentials via env (never hardcoded):
  KIOSK_LOAD_USER
  KIOSK_LOAD_PASSWORD
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import httpx
import websockets

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / ".cache"
FACE_CACHE = CACHE_DIR / "sample_face.jpg"

DEFAULT_COMPANY = "11111111-1111-1111-1111-111111111111"
DEFAULT_MEMBER = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"
FACE_URL = (
    "https://raw.githubusercontent.com/deepinsight/insightface/master/"
    "python-package/insightface/data/images/t1.jpg"
)
DEFAULT_LAT = 13.7563
DEFAULT_LON = 100.5018

DETECT_INTERVAL_MS = 90
IDENTIFY_EVERY_MS = 1200
MAX_CONCURRENT_IDENTIFY = 2
MAX_CONCURRENT_CHECKIN = 3

SLO_SESSION_P95_MS = 500.0
SLO_DETECT_P95_MS = 550.0
SLO_DROPPED_RATE = 0.05


class Fail(Exception):
    pass


@dataclass
class LatencyBucket:
    samples_ms: list[float] = field(default_factory=list)
    errors: int = 0
    dropped: int = 0
    ok: int = 0
    duplicate: int = 0
    checked_in: int = 0

    def add(self, ms: float, *, dropped: bool = False) -> None:
        self.samples_ms.append(ms)
        if dropped:
            self.dropped += 1
        else:
            self.ok += 1

    def add_error(self) -> None:
        self.errors += 1

    def percentile(self, p: float) -> Optional[float]:
        if not self.samples_ms:
            return None
        ordered = sorted(self.samples_ms)
        if len(ordered) == 1:
            return ordered[0]
        idx = (len(ordered) - 1) * (p / 100.0)
        lo = int(idx)
        hi = min(lo + 1, len(ordered) - 1)
        frac = idx - lo
        return ordered[lo] * (1 - frac) + ordered[hi] * frac

    def summary(self) -> dict[str, Any]:
        n = len(self.samples_ms)
        drop_rate = (self.dropped / n) if n else 0.0
        return {
            "count": n,
            "ok": self.ok,
            "dropped": self.dropped,
            "errors": self.errors,
            "duplicate": self.duplicate,
            "checked_in": self.checked_in,
            "dropped_rate": round(drop_rate, 4),
            "p50_ms": round(self.percentile(50) or 0, 1) if n else None,
            "p95_ms": round(self.percentile(95) or 0, 1) if n else None,
            "mean_ms": round(statistics.fmean(self.samples_ms), 1) if n else None,
        }


@dataclass
class RunStats:
    session: LatencyBucket = field(default_factory=LatencyBucket)
    detect: LatencyBucket = field(default_factory=LatencyBucket)
    identify: LatencyBucket = field(default_factory=LatencyBucket)
    checkin: LatencyBucket = field(default_factory=LatencyBucket)
    reconnects: int = 0
    face_core_down: int = 0

    def merge(self, other: "RunStats") -> None:
        for name in ("session", "detect", "identify", "checkin"):
            src: LatencyBucket = getattr(other, name)
            dst: LatencyBucket = getattr(self, name)
            dst.samples_ms.extend(src.samples_ms)
            dst.errors += src.errors
            dst.dropped += src.dropped
            dst.ok += src.ok
            dst.duplicate += src.duplicate
            dst.checked_in += src.checked_in
        self.reconnects += other.reconnects
        self.face_core_down += other.face_core_down


def http_to_ws(base_url: str) -> str:
    parsed = urlparse(base_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/face/ws/kiosk", "", "", ""))


def require_creds() -> tuple[str, str]:
    user = os.environ.get("KIOSK_LOAD_USER", "").strip()
    password = os.environ.get("KIOSK_LOAD_PASSWORD", "").strip()
    if not user or not password:
        raise Fail(
            "Set KIOSK_LOAD_USER and KIOSK_LOAD_PASSWORD "
            "(demo local: admin / Password123! after seed)"
        )
    return user, password


def login(base_url: str, user: str, password: str) -> str:
    url = f"{base_url.rstrip('/')}/auth/login"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json={"username": user, "password": password})
        if resp.status_code != 200:
            raise Fail(f"login failed HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        token = data.get("access_token") or data.get("accessToken")
        if not token:
            raise Fail(f"login response missing access_token: {data}")
        return str(token)


def ensure_face_image() -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if FACE_CACHE.is_file() and FACE_CACHE.stat().st_size > 1000:
        return FACE_CACHE.read_bytes()
    print(f"Downloading sample face -> {FACE_CACHE}")
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(FACE_URL)
        resp.raise_for_status()
        if len(resp.content) < 1000:
            raise Fail("sample face download too small")
        FACE_CACHE.write_bytes(resp.content)
        return resp.content


def prepare_enroll(
    base_url: str,
    token: str,
    member_id: str,
    image: bytes,
) -> None:
    url = f"{base_url.rstrip('/')}/face/members/{member_id}/add-face"
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("face.jpg", image, "image/jpeg")}
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, headers=headers, files=files)
        if resp.status_code not in (200, 201):
            raise Fail(f"add-face failed HTTP {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        face_id = data.get("faceEncodingId")
        if not face_id:
            raise Fail(f"add-face missing faceEncodingId: {data}")
        print(f"  enrolled member {member_id} -> faceEncodingId={face_id}")


def image_b64(image: bytes) -> str:
    return base64.b64encode(image).decode("ascii")


def prepare_frame(
    image: bytes,
    count: int,
    *,
    frame_width: int = 1280,
    jpeg_quality: int = 70,
) -> bytes:
    """Build a detect frame sized like a real kiosk canvas.

    Multi-face mosaics are tiled then downscaled so width ≤ frame_width
    (default 1280) at jpeg_quality ~70 — matching the Angular kiosk
    (quality 0.7), not a full-res 3× mosaic (~3936 px / ~500 KB).
    """
    from io import BytesIO

    from PIL import Image

    face = Image.open(BytesIO(image)).convert("RGB")
    count = max(1, int(count))
    if count <= 1:
        canvas = face
    else:
        # Prefer a wide row so faces stay separated (helps detector NMS).
        cols = min(count, 3)
        rows = (count + cols - 1) // cols
        gap = 24
        cell_w, cell_h = face.size
        canvas = Image.new(
            "RGB",
            (cols * cell_w + (cols + 1) * gap, rows * cell_h + (rows + 1) * gap),
            (32, 32, 32),
        )
        for i in range(count):
            r, c = divmod(i, cols)
            x = gap + c * (cell_w + gap)
            y = gap + r * (cell_h + gap)
            canvas.paste(face, (x, y))

    max_w = max(320, int(frame_width))
    if canvas.size[0] > max_w:
        ratio = max_w / float(canvas.size[0])
        new_size = (max_w, max(1, int(round(canvas.size[1] * ratio))))
        canvas = canvas.resize(new_size, Image.Resampling.LANCZOS)

    quality = max(40, min(95, int(jpeg_quality)))
    out = BytesIO()
    canvas.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


# Back-compat alias used by older docs / callers.
def mosaic_faces(image: bytes, count: int) -> bytes:
    return prepare_frame(image, count)


def append_jsonl(path: Optional[Path], row: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class KioskClient:
    """One simulated kiosk screen."""

    def __init__(
        self,
        *,
        kiosk_id: int,
        ws_url: str,
        token: str,
        company_id: str,
        lat: float,
        lon: float,
        detect_b64: str,
        crop_b64: str,
        faces_per_kiosk: int,
        profile: str,
        hold_s: float,
        jsonl: Optional[Path],
        step_label: str,
        rate: float = 0.0,
        max_inflight: int = 8,
        detect_interval_ms: float = DETECT_INTERVAL_MS,
    ) -> None:
        self.kiosk_id = kiosk_id
        self.ws_url = ws_url
        self.token = token
        self.company_id = company_id
        self.lat = lat
        self.lon = lon
        self.detect_b64 = detect_b64
        self.crop_b64 = crop_b64
        self.faces_per_kiosk = max(1, faces_per_kiosk)
        self.profile = profile
        self.hold_s = hold_s
        self.jsonl = jsonl
        self.step_label = step_label
        # Open-loop stress: send detect at --rate jobs/s without waiting.
        self.rate = float(rate)
        self.max_inflight = max(1, int(max_inflight))
        self.detect_interval_ms = float(detect_interval_ms)
        self.stats = RunStats()
        self._pending: dict[str, asyncio.Future] = {}
        self._identify_inflight = 0
        self._checkin_inflight = 0
        self._detect_inflight = 0
        self._last_identify_at: dict[int, float] = {}
        self._stop = False
        self._track_ids = list(range(1, self.faces_per_kiosk + 1))

    def _log(self, event: str, **extra: Any) -> None:
        row = {
            "ts": time.time(),
            "step": self.step_label,
            "kiosk": self.kiosk_id,
            "event": event,
            **extra,
        }
        append_jsonl(self.jsonl, row)

    async def _receiver(self, ws) -> None:
        while not self._stop:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                return
            msg = json.loads(raw)
            if msg.get("type") == "error" and msg.get("code") == "face_core_down":
                self.stats.face_core_down += 1
                self._log("face_core_down", detail=msg.get("detail"))
            req_id = msg.get("requestId")
            if req_id and req_id in self._pending:
                fut = self._pending.pop(req_id)
                if not fut.done():
                    fut.set_result(msg)

    async def _wait_key(self, key: str, timeout: float = 30.0) -> dict:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[key] = fut
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(key, None)
            raise Fail(f"kiosk {self.kiosk_id}: timeout waiting for {key}")

    async def run(self) -> RunStats:
        bg_tasks: list[asyncio.Task] = []
        try:
            async with websockets.connect(
                self.ws_url,
                open_timeout=30,
                max_size=8 * 1024 * 1024,
            ) as ws:
                # Handshake before the multiplexed receiver (avoids ready race).
                ready = json.loads(await asyncio.wait_for(ws.recv(), timeout=15.0))
                if ready.get("type") != "ready":
                    raise Fail(f"expected ready, got {ready}")

                t0 = time.perf_counter()
                await ws.send(
                    json.dumps(
                        {
                            "type": "session",
                            "companyId": self.company_id,
                            "token": self.token,
                            "latitude": self.lat,
                            "longitude": self.lon,
                        }
                    )
                )
                session_ok = json.loads(
                    await asyncio.wait_for(ws.recv(), timeout=15.0)
                )
                session_ms = (time.perf_counter() - t0) * 1000
                if session_ok.get("type") != "session_ok":
                    self.stats.session.add_error()
                    raise Fail(f"session failed: {session_ok}")
                self.stats.session.add(session_ms)
                self._log("session_ok", latency_ms=round(session_ms, 1))

                recv_task = asyncio.create_task(self._receiver(ws))
                try:
                    deadline = time.monotonic() + self.hold_s
                    if self.profile == "stress":
                        await self._run_stress(ws, deadline)
                    else:
                        while time.monotonic() < deadline:
                            bg_tasks = [t for t in bg_tasks if not t.done()]
                            task = await self._tick(ws)
                            if task is not None:
                                bg_tasks.append(task)
                finally:
                    self._stop = True
                    if bg_tasks:
                        await asyncio.gather(*bg_tasks, return_exceptions=True)
                    recv_task.cancel()
                    try:
                        await recv_task
                    except asyncio.CancelledError:
                        pass
        except Exception as exc:
            self._log("error", detail=str(exc))
            raise
        return self.stats

    async def _run_stress(self, ws, deadline: float) -> None:
        """Open-loop detect: fire at --rate without waiting for each reply."""
        interval = 1.0 / self.rate if self.rate > 0 else DETECT_INTERVAL_MS / 1000.0
        next_send = time.monotonic()
        inflight: set[asyncio.Task] = set()

        while time.monotonic() < deadline:
            now = time.monotonic()
            # Reap finished waiters.
            done = {t for t in inflight if t.done()}
            for t in done:
                inflight.discard(t)
                try:
                    t.result()
                except Exception:
                    pass

            if self._detect_inflight >= self.max_inflight:
                await asyncio.sleep(0.002)
                continue

            if now < next_send:
                await asyncio.sleep(min(0.002, next_send - now))
                continue

            next_send = max(next_send + interval, time.monotonic())
            task = asyncio.create_task(self._detect_open_loop(ws))
            inflight.add(task)

        if inflight:
            await asyncio.gather(*inflight, return_exceptions=True)

    async def _detect_open_loop(self, ws) -> None:
        detect_id = f"d-{self.kiosk_id}-{uuid.uuid4().hex[:10]}"
        self._detect_inflight += 1
        t0 = time.perf_counter()
        try:
            await ws.send(
                json.dumps(
                    {
                        "type": "detect",
                        "requestId": detect_id,
                        "image": self.detect_b64,
                    }
                )
            )
            try:
                detected = await self._wait_key(detect_id, timeout=20.0)
            except Fail:
                self.stats.detect.add_error()
                self._log("detect_timeout", requestId=detect_id)
                return
            detect_ms = (time.perf_counter() - t0) * 1000
            dropped = bool(detected.get("dropped"))
            face_n = len(detected.get("faces") or [])
            self.stats.detect.add(detect_ms, dropped=dropped)
            self._log(
                "detected",
                latency_ms=round(detect_ms, 1),
                dropped=dropped,
                faces=face_n,
                want_faces=self.faces_per_kiosk,
                open_loop=True,
            )
        finally:
            self._detect_inflight = max(0, self._detect_inflight - 1)

    async def _tick(self, ws) -> Optional[asyncio.Task]:
        detect_id = f"d-{self.kiosk_id}-{uuid.uuid4().hex[:10]}"
        t0 = time.perf_counter()
        await ws.send(
            json.dumps(
                {
                    "type": "detect",
                    "requestId": detect_id,
                    "image": self.detect_b64,
                }
            )
        )
        try:
            detected = await self._wait_key(detect_id, timeout=20.0)
        except Fail:
            self.stats.detect.add_error()
            await asyncio.sleep(self.detect_interval_ms / 1000.0)
            return None

        detect_ms = (time.perf_counter() - t0) * 1000
        dropped = bool(detected.get("dropped"))
        face_n = len(detected.get("faces") or [])
        self.stats.detect.add(detect_ms, dropped=dropped)
        self._log(
            "detected",
            latency_ms=round(detect_ms, 1),
            dropped=dropped,
            faces=face_n,
            want_faces=self.faces_per_kiosk,
        )

        bg: Optional[asyncio.Task] = None
        # Drive people-load from --faces-per-kiosk (UI track count), even if
        # mosaic NMS returns fewer boxes — still log actual face_n above.
        people = self.faces_per_kiosk if (not dropped and face_n > 0) else 0
        if self.profile in ("rush", "identify") and people > 0:
            bg = asyncio.create_task(self._people_side(ws, people))

        await asyncio.sleep(self.detect_interval_ms / 1000.0)
        return bg

    async def _people_side(self, ws, people: int) -> None:
        """Identify (+ optional check-in for rush) driven by faces-per-kiosk."""
        tasks: list[asyncio.Task] = []
        now = time.monotonic()
        identify_budget = min(people, MAX_CONCURRENT_IDENTIFY)
        for track_id in self._track_ids[:identify_budget]:
            if self._identify_inflight >= MAX_CONCURRENT_IDENTIFY:
                break
            last = self._last_identify_at.get(track_id, 0.0)
            if (now - last) * 1000 < IDENTIFY_EVERY_MS:
                continue
            self._last_identify_at[track_id] = now
            # Reserve slot before create_task so parallel starts respect the cap.
            self._identify_inflight += 1
            tasks.append(asyncio.create_task(self._do_identify(ws, track_id, reserved=True)))

        if self.profile == "rush":
            checkin_budget = min(people, MAX_CONCURRENT_CHECKIN)
            started_checkin = 0
            for track_id in self._track_ids[:checkin_budget]:
                if self._checkin_inflight + started_checkin >= MAX_CONCURRENT_CHECKIN:
                    break
                started_checkin += 1
                self._checkin_inflight += 1
                tasks.append(
                    asyncio.create_task(self._do_checkin(ws, track_id, reserved=True))
                )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _rush_side(self, ws, people: int) -> None:
        # Back-compat alias
        await self._people_side(ws, people)

    async def _do_identify(self, ws, track_id: int, *, reserved: bool = False) -> None:
        if not reserved:
            if self._identify_inflight >= MAX_CONCURRENT_IDENTIFY:
                return
            self._identify_inflight += 1
        req_id = f"i-{self.kiosk_id}-{track_id}-{uuid.uuid4().hex[:8]}"
        t0 = time.perf_counter()
        try:
            await ws.send(
                json.dumps(
                    {
                        "type": "identify",
                        "trackId": track_id,
                        "requestId": req_id,
                        "image": self.crop_b64,
                    }
                )
            )
            msg = await self._wait_key(req_id, timeout=60.0)
            ms = (time.perf_counter() - t0) * 1000
            if msg.get("type") == "error":
                self.stats.identify.add_error()
                self._log(
                    "identify_error",
                    trackId=track_id,
                    detail=msg.get("detail"),
                    latency_ms=round(ms, 1),
                )
            else:
                self.stats.identify.add(ms)
                self._log(
                    "identified",
                    trackId=track_id,
                    latency_ms=round(ms, 1),
                    memberId=msg.get("memberId"),
                    matched=msg.get("matched"),
                )
        except Fail:
            self.stats.identify.add_error()
            self._log("identify_timeout", trackId=track_id)
        finally:
            self._identify_inflight = max(0, self._identify_inflight - 1)

    async def _do_checkin(self, ws, track_id: int, *, reserved: bool = False) -> None:
        if not reserved:
            if self._checkin_inflight >= MAX_CONCURRENT_CHECKIN:
                return
            self._checkin_inflight += 1
        req_id = f"c-{self.kiosk_id}-{track_id}-{uuid.uuid4().hex[:8]}"
        t0 = time.perf_counter()
        try:
            await ws.send(
                json.dumps(
                    {
                        "type": "checkin",
                        "trackId": track_id,
                        "requestId": req_id,
                        "images": [self.crop_b64],
                        "latitude": self.lat,
                        "longitude": self.lon,
                        "note": "kiosk load test",
                    }
                )
            )
            msg = await self._wait_key(req_id, timeout=60.0)
            ms = (time.perf_counter() - t0) * 1000
            if msg.get("type") == "error":
                self.stats.checkin.add_error()
                self._log(
                    "checkin_error",
                    trackId=track_id,
                    detail=msg.get("detail"),
                    latency_ms=round(ms, 1),
                )
            else:
                self.stats.checkin.add(ms)
                if msg.get("duplicate"):
                    self.stats.checkin.duplicate += 1
                if msg.get("checkedIn"):
                    self.stats.checkin.checked_in += 1
                self._log(
                    "checked_in",
                    trackId=track_id,
                    latency_ms=round(ms, 1),
                    checkedIn=bool(msg.get("checkedIn")),
                    duplicate=bool(msg.get("duplicate")),
                    memberId=msg.get("memberId"),
                )
        except Fail:
            self.stats.checkin.add_error()
            self._log("checkin_timeout", trackId=track_id)
        finally:
            self._checkin_inflight = max(0, self._checkin_inflight - 1)


def print_summary(label: str, stats: RunStats) -> None:
    print(f"\n=== {label} ===")
    for name in ("session", "detect", "identify", "checkin"):
        bucket: LatencyBucket = getattr(stats, name)
        s = bucket.summary()
        if s["count"] == 0 and s["errors"] == 0:
            continue
        extra = ""
        if name == "detect":
            extra = f"  dropped_rate={s['dropped_rate']:.1%}"
        if name == "checkin":
            extra = f"  checked_in={s['checked_in']} duplicate={s['duplicate']}"
        print(
            f"  {name:10s}  n={s['count']:5d}  "
            f"p50={s['p50_ms']} ms  p95={s['p95_ms']} ms  "
            f"errors={s['errors']}{extra}"
        )
    if stats.face_core_down:
        print(f"  face_core_down events: {stats.face_core_down}")
    if stats.reconnects:
        print(f"  reconnects: {stats.reconnects}")


def check_slo(stats: RunStats) -> list[str]:
    violations: list[str] = []
    session_p95 = stats.session.percentile(95)
    if session_p95 is not None and session_p95 > SLO_SESSION_P95_MS:
        violations.append(
            f"session p95 {session_p95:.1f} ms > {SLO_SESSION_P95_MS} ms"
        )
    detect_p95 = stats.detect.percentile(95)
    if detect_p95 is not None and detect_p95 > SLO_DETECT_P95_MS:
        violations.append(
            f"detect p95 {detect_p95:.1f} ms > {SLO_DETECT_P95_MS} ms"
        )
    n = len(stats.detect.samples_ms)
    if n:
        rate = stats.detect.dropped / n
        if rate > SLO_DROPPED_RATE:
            violations.append(
                f"detect dropped_rate {rate:.1%} > {SLO_DROPPED_RATE:.0%}"
            )
    return violations


async def run_step(
    *,
    n_kiosks: int,
    ws_url: str,
    token: str,
    company_id: str,
    lat: float,
    lon: float,
    detect_b64: str,
    crop_b64: str,
    faces_per_kiosk: int,
    profile: str,
    hold_s: float,
    jsonl: Optional[Path],
    rate: float = 0.0,
    max_inflight: int = 8,
    detect_interval_ms: float = DETECT_INTERVAL_MS,
) -> RunStats:
    label = (
        f"kiosks={n_kiosks} faces/kiosk={faces_per_kiosk} "
        f"profile={profile} hold={hold_s}s"
    )
    if profile == "stress" and rate > 0:
        label += f" rate={rate:g}/s"
    if detect_interval_ms != DETECT_INTERVAL_MS:
        label += f" detect_ms={detect_interval_ms:g}"
    print(f"\n--- Starting {label} ---")
    clients = [
        KioskClient(
            kiosk_id=i,
            ws_url=ws_url,
            token=token,
            company_id=company_id,
            lat=lat,
            lon=lon,
            detect_b64=detect_b64,
            crop_b64=crop_b64,
            faces_per_kiosk=faces_per_kiosk,
            profile=profile,
            hold_s=hold_s,
            jsonl=jsonl,
            step_label=label,
            rate=rate,
            max_inflight=max_inflight,
            detect_interval_ms=detect_interval_ms,
        )
        for i in range(n_kiosks)
    ]
    results = await asyncio.gather(
        *[c.run() for c in clients],
        return_exceptions=True,
    )
    merged = RunStats()
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  kiosk {i} failed: {result}", file=sys.stderr)
            merged.session.add_error()
            continue
        merged.merge(result)
    print_summary(label, merged)
    detect_n = len(merged.detect.samples_ms)
    sent_per_s = (detect_n / hold_s) if hold_s > 0 else 0.0
    append_jsonl(
        jsonl,
        {
            "ts": time.time(),
            "event": "step_summary",
            "step": label,
            "session": merged.session.summary(),
            "detect": merged.detect.summary(),
            "identify": merged.identify.summary(),
            "checkin": merged.checkin.summary(),
            "face_core_down": merged.face_core_down,
            "throughput_detect_per_s": round(sent_per_s, 2),
            "rate_target": rate if profile == "stress" else None,
        },
    )
    if profile == "stress":
        print(
            f"  open-loop throughput≈{sent_per_s:.1f} detect/s "
            f"(target {rate:g}/s × {n_kiosks} kiosks)"
        )
    return merged


def parse_kiosks(raw: str) -> list[int]:
    values = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)
        if n < 1:
            raise argparse.ArgumentTypeError("kiosk count must be >= 1")
        values.append(n)
    if not values:
        raise argparse.ArgumentTypeError("provide at least one kiosk count")
    return values


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Load-test DPU face kiosk WebSocket from the host"
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("KIOSK_LOAD_BASE_URL", "http://localhost:8880"),
        help="HTTP base (nginx). Default: http://localhost:8880",
    )
    p.add_argument(
        "--company-id",
        default=os.environ.get("KIOSK_LOAD_COMPANY_ID", DEFAULT_COMPANY),
    )
    p.add_argument(
        "--member-id",
        default=os.environ.get("KIOSK_LOAD_MEMBER_ID", DEFAULT_MEMBER),
        help="Member used by --prepare (demo emp1)",
    )
    p.add_argument("--lat", type=float, default=DEFAULT_LAT)
    p.add_argument("--lon", type=float, default=DEFAULT_LON)
    p.add_argument(
        "--profile",
        choices=("idle", "identify", "rush", "stress"),
        default="idle",
        help=(
            "idle=detect only; identify=detect+identify (no check-in); "
            "rush=detect+identify+checkin; stress=open-loop detect at --rate"
        ),
    )
    p.add_argument(
        "--kiosks",
        type=parse_kiosks,
        default="1",
        help="Comma-separated concurrent kiosk counts, e.g. 1,2,4",
    )
    p.add_argument(
        "--hold",
        type=float,
        default=30.0,
        help="Seconds to hold each kiosk step",
    )
    p.add_argument(
        "--faces-per-kiosk",
        type=int,
        default=1,
        help=(
            "People simulated per screen (mosaic detect + up to 2 identify / "
            "3 check-in in flight, matching UI caps). Default 1."
        ),
    )
    p.add_argument(
        "--frame-width",
        type=int,
        default=int(os.environ.get("KIOSK_LOAD_FRAME_WIDTH", "1280")),
        help="Max detect-frame width in px (default 1280, like a real kiosk)",
    )
    p.add_argument(
        "--jpeg-quality",
        type=int,
        default=int(os.environ.get("KIOSK_LOAD_JPEG_QUALITY", "70")),
        help="JPEG quality for detect frames (default 70 ≈ UI quality 0.7)",
    )
    p.add_argument(
        "--rate",
        type=float,
        default=float(os.environ.get("KIOSK_LOAD_RATE", "0")),
        help=(
            "Open-loop detect sends per second PER kiosk (stress profile). "
            "0 = use 1000/90 ≈ 11.1/s. Total target ≈ rate × kiosks."
        ),
    )
    p.add_argument(
        "--max-inflight",
        type=int,
        default=8,
        help="Max in-flight detect requests per kiosk in stress mode (default 8)",
    )
    p.add_argument(
        "--detect-interval-ms",
        type=float,
        default=float(os.environ.get("KIOSK_LOAD_DETECT_INTERVAL_MS", str(DETECT_INTERVAL_MS))),
        help=(
            "Closed-loop detect pacing in ms (idle/identify/rush). Default 90 (full-rate loadgen). "
            "Use 600–2000 to approximate kiosk motion-gating on a static scene."
        ),
    )
    p.add_argument(
        "--prepare",
        action="store_true",
        help="Download sample face + enroll member before load",
    )
    p.add_argument(
        "--jsonl",
        type=Path,
        default=None,
        help="Append per-event + step summaries as JSONL",
    )
    p.add_argument(
        "--fail-on-slo",
        action="store_true",
        help=(
            f"Exit 1 if session p95>{SLO_SESSION_P95_MS}ms, "
            f"detect p95>{SLO_DETECT_P95_MS}ms, or dropped_rate>{int(SLO_DROPPED_RATE * 100)} percent"
        ),
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    # argparse default for --kiosks is a string when default="1"; normalize
    if isinstance(args.kiosks, str):
        args.kiosks = parse_kiosks(args.kiosks)

    try:
        user, password = require_creds()
        print(f"Base URL: {args.base_url}")
        print(f"WS URL:   {http_to_ws(args.base_url)}")
        print(f"Login as: {user}")

        token = login(args.base_url, user, password)
        print("  login OK")

        image = ensure_face_image()
        print(f"  face image {len(image)} bytes ({FACE_CACHE})")

        if args.prepare:
            print(f"Preparing enroll for member {args.member_id} ...")
            prepare_enroll(args.base_url, token, args.member_id, image)

        faces = max(1, int(args.faces_per_kiosk))
        mosaic = prepare_frame(
            image,
            faces,
            frame_width=args.frame_width,
            jpeg_quality=args.jpeg_quality,
        )
        # Single-face crop for identify/check-in stays full sample size.
        crop = prepare_frame(
            image, 1, frame_width=args.frame_width, jpeg_quality=args.jpeg_quality
        )
        crop_b64 = image_b64(crop)
        detect_b64 = image_b64(mosaic)
        print(
            f"  faces/kiosk={faces}  detect frame={len(mosaic)} bytes "
            f"(max_w={args.frame_width} q={args.jpeg_quality})"
        )

        rate = float(args.rate)
        if args.profile == "stress" and rate <= 0:
            rate = 1000.0 / DETECT_INTERVAL_MS  # ~11.1/s per kiosk

        ws_url = http_to_ws(args.base_url)
        overall = RunStats()
        step_stats: list[tuple[int, RunStats]] = []

        for n in args.kiosks:
            stats = asyncio.run(
                run_step(
                    n_kiosks=n,
                    ws_url=ws_url,
                    token=token,
                    company_id=args.company_id,
                    lat=args.lat,
                    lon=args.lon,
                    detect_b64=detect_b64,
                    crop_b64=crop_b64,
                    faces_per_kiosk=faces,
                    profile=args.profile,
                    hold_s=args.hold,
                    jsonl=args.jsonl,
                    rate=rate,
                    max_inflight=args.max_inflight,
                    detect_interval_ms=args.detect_interval_ms,
                )
            )
            overall.merge(stats)
            step_stats.append((n, stats))

        print_summary("OVERALL", overall)

        if args.fail_on_slo:
            # Evaluate SLO on the largest kiosk step (most stressing)
            worst = step_stats[-1][1] if step_stats else overall
            violations = check_slo(worst)
            if violations:
                print("\nSLO FAILED:", file=sys.stderr)
                for v in violations:
                    print(f"  - {v}", file=sys.stderr)
                return 1
            print("\nSLO OK")

        return 0
    except Fail as exc:
        print(f"\nFAIL  {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
