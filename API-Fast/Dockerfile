# syntax=docker/dockerfile:1
# GPU API image: NVIDIA CUDA 12.8 + cuDNN runtime (RTX 50-series friendly), ONNX Runtime GPU.
# Host needs the NVIDIA driver + NVIDIA Container Toolkit.
# Build: docker compose build api
#
# Two stages: `builder` compiles wheels (insightface has a Cython extension) and warms the
# buffalo_l model; `runtime` only carries python3, the venv, the model and the source and
# runs as the unprivileged user `app` (uid 10001). Base images are pinned by digest.
ARG CUDA_BASE=nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04@sha256:ac55d124da4882b497f732d8dfd9a702d5447a5f29d08d56da6f64f0a1eb34bc

FROM ${CUDA_BASE} AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        python3-venv \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    # pip is not needed in the runtime image (immutable venv); dropping it also removes its vendored SBOM
    && python -m pip uninstall -y pip

# Warm buffalo_l into a fixed home so the runtime user never needs network or a writable
# ~/.insightface (insightface resolves models from $HOME/.insightface).
RUN HOME=/opt/model-home python -c "from insightface.app import FaceAnalysis; \
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
app.prepare(ctx_id=-1, det_size=(640, 640)); \
print('InsightFace buffalo_l ready')"


FROM ${CUDA_BASE} AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/opt/venv/bin:$PATH \
    HOME=/home/app \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Runtime-only system libraries (OpenCV headless / ONNX Runtime). No compiler, no pip cache.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid ${APP_GID} app \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --home-dir /home/app --create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=${APP_UID}:${APP_GID} /opt/model-home/.insightface /home/app/.insightface

WORKDIR /app
COPY --chown=${APP_UID}:${APP_GID} . .

# Image volumes (uploaded / enrolled / temp) are owned by `app`; existing root-owned volumes
# from pre-B4 deployments must be chown'ed once — see docs/RUNBOOK.md "Upgrade to non-root".
RUN mkdir -p enrolled_images uploaded_images temp_images import_jobs video_clips \
    && chown -R ${APP_UID}:${APP_GID} /app

USER ${APP_UID}:${APP_GID}

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=180s --retries=12 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

# nvidia/cuda image sets an nvidia entrypoint; keep it but ensure CMD is clear
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
