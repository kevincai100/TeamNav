FROM node:24-bookworm-slim AS web-dependencies
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

FROM web-dependencies AS web-build
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace @teamnav/web
RUN rm -rf /workspace/apps/web/.next/standalone/node_modules/sharp \
    /workspace/apps/web/.next/standalone/node_modules/@img

FROM python:3.12-slim AS api-build
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY apps/api /workspace/apps/api
COPY packages /workspace/packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip wheel --no-cache-dir --wheel-dir /wheels /workspace/apps/api \
    && rm -rf /var/lib/apt/lists/*

FROM node:24-bookworm-slim AS node-runtime

FROM python:3.12-slim AS runtime
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    API_INTERNAL_URL=http://127.0.0.1:8000 \
    APP_URL=http://localhost:8080 \
    CORS_ORIGINS=http://localhost:8080 \
    DATABASE_URL=sqlite+aiosqlite:////data/teamnav.db \
    FORWARDED_ALLOW_IPS=127.0.0.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 libstdc++6 nginx \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system teamnav \
    && useradd --system --gid teamnav --home-dir /workspace teamnav \
    && mkdir -p /data \
    && chown teamnav:teamnav /data

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY apps/api /workspace/apps/api
COPY packages /workspace/packages
COPY --from=api-build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels teamnav-api \
    && rm -rf /wheels

COPY --from=web-build --chown=teamnav:teamnav /workspace/apps/web/.next/standalone /workspace
COPY --from=web-build --chown=teamnav:teamnav /workspace/apps/web/.next/static /workspace/apps/web/.next/static
COPY --chown=teamnav:teamnav deploy/aio/supervisor.py /usr/local/bin/teamnav-aio-supervisor.py
COPY deploy/aio/nginx.conf /etc/nginx/teamnav-aio.conf
RUN chown -R teamnav:teamnav /workspace

USER teamnav
EXPOSE 8080
VOLUME ["/data"]
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=10s --timeout=5s --retries=10 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=5)"]
ENTRYPOINT ["python", "/usr/local/bin/teamnav-aio-supervisor.py"]
