FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY apps/api /workspace/apps/api
COPY packages /workspace/packages
RUN pip install --no-cache-dir /workspace/apps/api
RUN groupadd --system teamnav \
    && useradd --system --gid teamnav --home-dir /workspace teamnav \
    && mkdir -p /data \
    && chown -R teamnav:teamnav /workspace /data
WORKDIR /workspace/apps/api
USER teamnav
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
