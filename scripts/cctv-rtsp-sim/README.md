# CCTV RTSP simulator (ffmpeg → MediaMTX smoke)

Synthetic RTSP camera for verifying the worker grab + event clip path **without a real LAN camera**.

## Bring up

From repo root (with your usual GPU/external-db overlays if needed):

```bash
docker compose -f docker-compose.yml -f docker-compose.rtsp-sim.yml up -d --build
```

Containers:

| Service | Role |
|---|---|
| `rtsp-sim` | MediaMTX accepting publish on path `loop` |
| `rtsp-sim-publisher` | ffmpeg `testsrc` → `rtsp://rtsp-sim:8554/loop` |

## Smoke checklist

1. Admin → Cameras → create camera  
   - **streamUrl:** `rtsp://rtsp-sim:8554/loop`  
   - **protocol:** `rtsp`  
   - **recordMode:** `event`  
   - **analysisEnabled:** on  
2. Company modules: enable **CCTV**.  
3. Cameras → **Ping** / **Snapshot** should succeed (via MediaMTX pull).  
4. Wait one worker tick (`WORKER_CCTV_INTERVAL_SECONDS`, default 15s) or watch `docker logs dpu-worker`.  
5. Playback → select the camera → **Export clip** (`waitForPost: false`)  
   - or wait for an incident clip after a face match.  
6. Open `/company/playback`, play + scrub; download uses authenticated blob.  
7. Optional Range probe:

```bash
# after login token in $TOKEN and CLIP_ID / COMPANY_ID set
curl -sI -H "Authorization: Bearer $TOKEN" \
  -H "Range: bytes=0-1023" \
  "http://localhost/cameras/company/$COMPANY_ID/clips/$CLIP_ID/download"
# expect HTTP/1.1 206 Partial Content
```

## Real camera follow-up

Point `streamUrl` at a LAN RTSP URL the **MediaMTX container** can reach (not only the browser host). Worker prefers `rtsp://mediamtx:8554/{cameraPath}` after Control API sync.
