# Lightweight load generator — run on the same Docker network as nginx.
# Build from repo root:
#   docker compose -f docker-compose.yml -f docker-compose.loadtest.yml build loadgen
FROM python:3.12-slim

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kiosk_load.py poll_queue.py summarize_capacity.py ./

# Sample face is downloaded on first --prepare / ensure_face_image()
RUN groupadd --gid ${APP_GID} app \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/.cache /results \
    && chown -R ${APP_UID}:${APP_GID} /app /results

ENV KIOSK_LOAD_BASE_URL=http://nginx:8080 \
    PYTHONUNBUFFERED=1

USER ${APP_UID}:${APP_GID}

ENTRYPOINT ["python", "kiosk_load.py"]
CMD ["--help"]
