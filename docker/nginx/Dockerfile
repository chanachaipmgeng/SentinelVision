# syntax=docker/dockerfile:1
# Gateway image: unprivileged nginx (uid 101, listens on 8080 / 8443), base pinned by digest.
# Config layout:
#   conf.d/00-dpu-http.conf   http-context maps, limit_req/limit_conn zones, body size
#   conf.d/default.conf       variant server block (compose overlays bind-mount dual/quad/hexa here)
#   conf.d/zz-tls.conf        optional 8443 listener, generated at start when TLS is enabled
#   snippets/*.conf           shared server body + proxy settings
#   /tmp/dpu-nginx/*.conf     rendered from env by /docker-entrypoint.d/30-dpu-runtime.sh
FROM nginxinc/nginx-unprivileged:1.30.6-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03

COPY 00-dpu-http.conf /etc/nginx/conf.d/00-dpu-http.conf
COPY default.conf /etc/nginx/conf.d/default.conf
COPY zz-tls.conf /etc/nginx/conf.d/zz-tls.conf
COPY snippets/ /etc/nginx/snippets/
COPY entrypoint/30-dpu-runtime.sh /docker-entrypoint.d/30-dpu-runtime.sh

USER root
# Strip CR from a possible Windows checkout, then validate the baked config once at build
# time with default toggles so a broken snippet fails the image build, not the deploy.
RUN sed -i 's/\r$//' /docker-entrypoint.d/30-dpu-runtime.sh /etc/nginx/conf.d/*.conf /etc/nginx/snippets/*.conf \
    && chmod 0755 /docker-entrypoint.d/30-dpu-runtime.sh \
    && /docker-entrypoint.d/30-dpu-runtime.sh \
    && nginx -t \
    && rm -rf /tmp/dpu-nginx /tmp/nginx.pid /tmp/*_temp
USER 101

EXPOSE 8080 8443

HEALTHCHECK --interval=20s --timeout=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
