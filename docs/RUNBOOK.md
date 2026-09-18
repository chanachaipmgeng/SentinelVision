# Runbook

## RPO / RTO
- RPO: 24 hours when `scripts/backup.sh` runs once a day.
- RTO: time to `psql` restore the dump plus copy `api_uploaded` / `api_enrolled` volumes.

## 502 after recreate
`docker compose up -d --build nginx` so the gateway re-resolves `api`. Check `GET /ready`.

## GPU driver mismatch
If `nvidia-smi` says driver/library mismatch, reboot the host so the kernel module matches the userspace libraries. Do not start `dpu-api` until `nvidia-smi` succeeds.

## 413 on import
Host TLS nginx must set `client_max_body_size 500m`. See `docker/nginx/tls-edge.example.conf`.

## Weak SECRET_KEY
The API refuses to start when `AUTH_FAIL_FAST=true` and `SECRET_KEY` is shorter than 32 characters or still `change-me-in-production`. Set a new secret and restart `api`. Existing tokens become invalid.

## Biometric data
Face vectors in `face_encoding` are required for matching. `enrolled_images` are gallery copies. Punch photos in `uploaded_images` are attendance evidence. `temp_images` can be deleted; the retention loop removes them after `TEMP_RETENTION_HOURS`.
