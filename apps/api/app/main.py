import asyncio
import time
import uuid
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.account import router as account_router
from app.api.admin import router as admin_router
from app.api.manage import router as manage_router
from app.api.sites import router as sites_router
from app.core.config import Settings, get_settings
from app.db import Database, create_database
from app.services.maintenance import maintenance_loop


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    current_settings = settings or get_settings()
    current_database = database or create_database(current_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        maintenance_task: asyncio.Task[None] | None = None
        if current_settings.link_check_scheduler_enabled:
            maintenance_task = asyncio.create_task(
                maintenance_loop(current_database, current_settings),
                name="teamnav-link-maintenance",
            )
        try:
            yield
        finally:
            if maintenance_task is not None:
                maintenance_task.cancel()
                with suppress(asyncio.CancelledError):
                    await maintenance_task

    app = FastAPI(
        title=current_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = current_settings
    app.state.database = current_database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def request_metadata(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(
            round((time.perf_counter() - started) * 1000, 2)
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> JSONResponse:
        try:
            async with current_database.sessions() as session:
                await session.execute(text("SELECT 1"))
            return JSONResponse({"status": "ready"})
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)

    app.include_router(sites_router)
    app.include_router(manage_router)
    app.include_router(admin_router)
    app.include_router(account_router)
    return app


app = create_app()
