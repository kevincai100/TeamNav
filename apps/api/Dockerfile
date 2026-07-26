FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY apps/api /workspace/apps/api
COPY packages /workspace/packages
RUN pip install --no-cache-dir /workspace/apps/api
WORKDIR /workspace/apps/api
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
