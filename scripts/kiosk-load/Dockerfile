# Lightweight load generator — run on the same Docker network as nginx.
# Build from repo root:
#   docker compose -f docker-compose.yml -f docker-compose.loadtest.yml build loadgen
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kiosk_load.py poll_queue.py summarize_capacity.py ./

# Sample face is downloaded on first --prepare / ensure_face_image()
RUN mkdir -p /app/.cache /results

ENV KIOSK_LOAD_BASE_URL=http://nginx:8080 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "kiosk_load.py"]
CMD ["--help"]
