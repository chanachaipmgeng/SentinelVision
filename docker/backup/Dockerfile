# Backup sidecar: PostgreSQL 16 client tools (must match the dpu-db major) + rclone for offsite copies.
# Runs scripts/backup.sh in "direct" mode on a timer; see docker-compose.backup.yml.
FROM rclone/rclone:1.76.0@sha256:7cbeec24a44f206067597c0368be4de90ae19a64d5113c7d1938bd737a81e466 AS rclone

FROM postgres:16.15-alpine@sha256:aa6cb33cf4c19c765cefcf48d96176258800870a9a1e930ad126200f9d825139

# rclone comes from the official image (current Go toolchain) rather than the Alpine package
COPY --from=rclone /usr/local/bin/rclone /usr/local/bin/rclone
RUN apk add --no-cache curl tar coreutils findutils \
    # the sidecar runs as a fixed non-root user; the server-only entrypoint helpers are not needed
    && rm -f /usr/local/bin/gosu /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-ensure-initdb.sh /usr/local/bin/docker-enforce-initdb.sh \
    && mkdir -p /opt/dpu/scripts/lib /data /backups \
    && chmod 1777 /backups

COPY scripts/lib/backup-common.sh /opt/dpu/scripts/lib/
COPY scripts/backup.sh scripts/restore.sh scripts/restore-drill.sh /opt/dpu/scripts/
COPY docker/backup/entrypoint.sh /opt/dpu/entrypoint.sh
RUN sed -i 's/\r$//' /opt/dpu/scripts/*.sh /opt/dpu/scripts/lib/*.sh /opt/dpu/entrypoint.sh \
    && chmod 0755 /opt/dpu/scripts/*.sh /opt/dpu/scripts/lib/*.sh /opt/dpu/entrypoint.sh

ENV BACKUP_MODE=direct \
    BACKUP_IMAGES_ROOT=/data \
    BACKUP_DIR=/backups \
    PGHOST=db \
    PGPORT=5432 \
    HOME=/tmp

# compose overrides the user; 1000 is a safe default for bind-mounted ./backups
USER 1000:1000
WORKDIR /opt/dpu
HEALTHCHECK --interval=5m --timeout=10s --start-period=1m --retries=3 \
  CMD test -f /tmp/backup-ok && test $(( $(date +%s) - $(cat /tmp/backup-ok) )) -lt $(( ${BACKUP_INTERVAL_SECONDS:-86400} * 2 + 3600 ))
ENTRYPOINT ["/opt/dpu/entrypoint.sh"]
