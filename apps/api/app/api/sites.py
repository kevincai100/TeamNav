from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import database_from_request, settings_from_request
from app.core.config import Settings
from app.core.security import token_digest
from app.db import Database, session_dependency
from app.models import AbuseReport
from app.schemas import PasswordUnlock, ReportCreate, SiteCreate
from app.services.auth import AccessAuth, AuthenticationError
from app.services.sites import RateLimitError, SiteDisabledError, SiteNotFoundError, SiteService

router = APIRouter(prefix="/api/v1")


async def get_session(
    database: Database = Depends(database_from_request),
) -> AsyncIterator[AsyncSession]:
    async for session in session_dependency(database):
        yield session


@router.post("/sites", status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    try:
        creator_ip = request.client.host if request.client else "unknown"
        return await SiteService(session, settings).create(data, creator_ip)
    except RateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail={"code": "CREATE_RATE_LIMITED"},
            headers={"Retry-After": "3600"},
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error


@router.get("/public/sites/{slug}")
async def public_site(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    service = SiteService(session, settings)
    try:
        site = await service.get_site(slug)
    except SiteNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "SITE_NOT_FOUND"}) from error
    except SiteDisabledError as error:
        raise HTTPException(status_code=410, detail={"code": "SITE_DISABLED"}) from error
    if not await AccessAuth(session, settings).is_authorized(
        site, request.cookies.get("teamnav_access")
    ):
        raise HTTPException(status_code=401, detail={"code": "PASSWORD_REQUIRED"})
    site.visit_count += 1
    await session.commit()
    return service.serialize(site, public=True)


@router.get("/public/sites/{slug}/metadata")
async def public_site_metadata(
    slug: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    try:
        site = await SiteService(session, settings).get_site(slug)
    except (SiteNotFoundError, SiteDisabledError) as error:
        raise HTTPException(status_code=404, detail={"code": "SITE_NOT_FOUND"}) from error
    protected = bool(site.access_password_hash)
    return {
        "name": settings.app_name if protected else site.name,
        "allow_indexing": site.allow_indexing and not protected,
    }


@router.post("/public/sites/{slug}/unlock", status_code=204)
async def unlock_public_site(
    slug: str,
    data: PasswordUnlock,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    service = SiteService(session, settings)
    try:
        site = await service.get_site(slug)
        token = await AccessAuth(session, settings).unlock(site, data.password)
    except (SiteNotFoundError, SiteDisabledError, AuthenticationError) as error:
        raise HTTPException(status_code=401, detail={"code": "INVALID_PASSWORD"}) from error
    response.set_cookie(
        "teamnav_access",
        token,
        max_age=settings.access_session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=f"/api/v1/public/sites/{slug}",
    )


@router.post("/public/sites/{slug}/reports", status_code=201)
async def report_public_site(
    slug: str,
    data: ReportCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, str]:
    service = SiteService(session, settings)
    try:
        site = await service.get_site(slug)
    except (SiteNotFoundError, SiteDisabledError) as error:
        raise HTTPException(status_code=404, detail={"code": "SITE_NOT_FOUND"}) from error
    ip = request.client.host if request.client else "unknown"
    report = AbuseReport(
        site_id=site.id,
        reason=data.reason,
        description=data.description,
        reporter_ip_hash=token_digest(ip, settings.secret_key),
    )
    session.add(report)
    await session.commit()
    return {"id": report.id, "status": report.status}
