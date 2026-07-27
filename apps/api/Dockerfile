FROM python:3.12-slim AS build
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY apps/api /workspace/apps/api
COPY packages /workspace/packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip wheel --no-cache-dir --wheel-dir /wheels /workspace/apps/api \
    && rm -rf /var/lib/apt/lists/*

FROM python:3.12-slim AS runtime
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY apps/api /workspace/apps/api
COPY packages /workspace/packages
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels teamnav-api \
    && rm -rf /wheels
RUN groupadd --system teamnav \
    && useradd --system --gid teamnav --home-dir /workspace teamnav \
    && mkdir -p /data \
    && chown -R teamnav:teamnav /workspace /data
WORKDIR /workspace/apps/api
USER teamnav
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
