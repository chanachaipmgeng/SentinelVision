# syntax=docker/dockerfile:1
# Multi-stage build: Angular 19 admin → unprivileged nginx static server (uid 101, port 8080).

FROM node:20.20.2-bookworm@sha256:8f693eaa7e0a8e71560c9a82b55fd54c2ae920a2ba5d2cde28bac7d1c01c9ba5 AS build
WORKDIR /app

ENV NODE_OPTIONS=--max-old-space-size=8192

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# assets/config.json is git-ignored; ship the placeholder so the asset exists. The runtime
# entrypoint rewrites it with an empty Maps key and GOOGLE_MAPS_MAP_ID on container start.
RUN [ -f src/assets/config.json ] || cp src/assets/config.example.json src/assets/config.json
RUN npx ng build --configuration=production

# Angular application builder output served by nginx-unprivileged:
#  - listens on 8080 (not 80), pid + temp dirs under /tmp → works with a read-only root fs
#    plus a tmpfs on /tmp (see docker-compose.prod.yml).
#  - /docker-entrypoint.d/ scripts run as the nginx user, so the runtime config is written to
#    /tmp/dpu-runtime/config.json and aliased at /assets/config.json (docker/nginx-spa.conf).
FROM nginxinc/nginx-unprivileged:1.30.6-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03 AS runtime
COPY docker/nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY docker/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
USER root
# Pull Alpine security fixes published after the pinned base digest was built (CI trivy gate
# fails on fixable HIGH/CRITICAL OS CVEs). Explicit libxslt bump busts BuildKit cache that
# otherwise reuses a pre-advisory `apk upgrade` layer (CVE-2026-125350 / 87636 / 9947).
RUN apk upgrade --no-cache \
    && apk add --no-cache --upgrade 'libxslt>=1.1.43-r4' \
    && sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh \
    && chmod 0755 /docker-entrypoint.d/40-runtime-config.sh \
    && rm -rf /usr/share/nginx/html/*
COPY --from=build --chown=root:root /app/dist/preview/browser /usr/share/nginx/html
USER 101
EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
