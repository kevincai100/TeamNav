from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import settings_from_request
from app.api.sites import get_session
from app.core.config import Settings
from app.models import AbuseReport, Site
from app.schemas import AdminSessionCreate, AdminSiteUpdate, ReportUpdate
from app.services.admin_auth import (
    AdminAuth,
    AdminAuthenticationError,
    AdminAuthorizationError,
)

router = APIRouter(prefix="/api/v1/admin")


def authorize_admin(request: Request, settings: Settings, *, mutation: bool) -> None:
    auth = AdminAuth(settings)
    try:
        payload = auth.authenticate(request.cookies.get("teamnav_admin"))
        if mutation:
            auth.check_csrf(payload, request.headers.get("X-CSRF-Token"))
    except AdminAuthenticationError as error:
        raise HTTPException(status_code=401, detail={"code": "ADMIN_SESSION_REQUIRED"}) from error
    except AdminAuthorizationError as error:
        raise HTTPException(status_code=403, detail={"code": "CSRF_FAILED"}) from error


@router.post("/session")
async def create_admin_session(
    data: AdminSessionCreate,
    response: Response,
    settings: Settings = Depends(settings_from_request),
) -> dict[str, str]:
    try:
        session_token, csrf_token = AdminAuth(settings).exchange(data.token)
    except AdminAuthenticationError as error:
        raise HTTPException(status_code=401, detail={"code": "INVALID_ADMIN_TOKEN"}) from error
    response.set_cookie(
        "teamnav_admin",
        session_token,
        max_age=settings.admin_session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/admin",
    )
    return {"csrf_token": csrf_token}


@router.get("/dashboard")
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    authorize_admin(request, settings, mutation=False)
    reports = list(
        (
            await session.scalars(
                select(AbuseReport).order_by(AbuseReport.created_at.desc()).limit(200)
            )
        ).all()
    )
    sites = list(
        (
            await session.scalars(
                select(Site)
                .where(Site.deleted_at.is_(None))
                .order_by(Site.created_at.desc())
                .limit(200)
            )
        ).all()
    )
    site_by_id = {site.id: site for site in sites}
    return {
        "reports": [
            {
                "id": report.id,
                "site_slug": site_by_id.get(report.site_id).public_slug
                if site_by_id.get(report.site_id)
                else None,
                "site_name": site_by_id.get(report.site_id).name
                if site_by_id.get(report.site_id)
                else "Deleted site",
                "reason": report.reason,
                "description": report.description,
                "status": report.status,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ],
        "sites": [
            {
                "public_slug": site.public_slug,
                "name": site.name,
                "is_disabled": site.is_disabled,
                "visit_count": site.visit_count,
                "created_at": site.created_at.isoformat(),
            }
            for site in sites
        ],
    }


@router.patch("/reports/{report_id}")
async def update_report(
    report_id: str,
    data: ReportUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    authorize_admin(request, settings, mutation=True)
    report = await session.get(AbuseReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND"})
    report.status = data.status
    await session.commit()
    return {"id": report.id, "status": report.status}


@router.patch("/sites/{slug}")
async def update_admin_site(
    slug: str,
    data: AdminSiteUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    authorize_admin(request, settings, mutation=True)
    site = await session.scalar(
        select(Site).where(Site.public_slug == slug, Site.deleted_at.is_(None))
    )
    if site is None:
        raise HTTPException(status_code=404, detail={"code": "SITE_NOT_FOUND"})
    site.is_disabled = data.is_disabled
    await session.commit()
    return {"public_slug": site.public_slug, "is_disabled": site.is_disabled}
