# Face PAD (Presentation Attack Detection)

Phase D8 adds an optional **ONNX PAD** path in `API-Fast/src/utils/liveness_detection.py` on top of the existing heuristic anti-spoof (YCrCb chrominance + specular glare).

Weights are **not** committed to git.

## Configure

| Variable | Default | Meaning |
|----------|---------|---------|
| `FACE_PAD_MODEL_PATH` | _(empty)_ | Absolute path to a MiniFASNet-compatible `.onnx` file inside the API container/host. Empty → heuristic only. |
| `FACE_PAD_MIN_LIVE_SCORE` | `0.80` | Minimum softmax “live” probability to accept. |
| `FACE_PAD_FAIL_CLOSED` | `true` | When a model path is set but inference fails, reject the frame. |
| `FACE_MODEL_VERSION` | `buffalo_l` | Written to `face_encoding.modelVersion` at enroll. |
| `ENROLL_QUALITY_GATE_ENABLED` | `true` | Reject enroll frames that fail size/pose/sharpness. |

Mount the weights read-only, for example:

```yaml
# docker-compose override fragment
services:
  api:
    volumes:
      - /opt/dpu/models/MiniFASNetV2.onnx:/models/pad.onnx:ro
    environment:
      FACE_PAD_MODEL_PATH: /models/pad.onnx
```

## Obtain weights

1. Use a MiniFASNet / Silent-Face-Anti-Spoofing ONNX export you are licensed to deploy (e.g. from the upstream Silent-Face-Anti-Spoofing project’s 2.7_80x80_MiniFASNetV2 checkpoint converted with their export script).
2. Place the file on the host (outside the repo) and point `FACE_PAD_MODEL_PATH` at it.
3. Confirm `/metrics` shows normal face GPU / match series after a live check-in; PAD failures surface as `ValueError` / HTTP 400 from the liveness path.

Expected input: BGR face crop resized to the model’s square size (auto-detected from ONNX, typically 80). Output: 2-class logits `[spoof, live]` or a single live logit.

## Enrollment quality gate

`utils/enrollment_quality.py` rejects enroll when:

- blur / brightness fail (`IMAGE_BLUR_THRESHOLD`, `IMAGE_BRIGHTNESS_*`)
- face area ratio &lt; `ENROLL_MIN_FACE_RATIO` (default 0.08)
- |yaw| / |roll| from 5-point landmarks exceed `ENROLL_MAX_YAW_DEG` / `ENROLL_MAX_ROLL_DEG`
- Laplacian sharpness &lt; `ENROLL_MIN_SHARPNESS`

## FAR / FRR metrics

Prometheus (see `/metrics`):

- `dpu_face_match_decisions_total{source,decision}`
- `dpu_face_match_distance{source,decision}`
- `dpu_face_far_events_total{source}` / `dpu_face_frr_events_total{source}` when a labeled `expected_member_id` is passed into `search_face_pgvector` (1:1 verify / eval harness)
