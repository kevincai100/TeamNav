from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import settings_from_request
from app.api.sites import get_session
from app.core.config import Settings
from app.models import Site
from app.schemas import AccountCredentials
from app.services.account_auth import (
    AccountAuth,
    AccountAuthenticationError,
    AccountConflictError,
)

router = APIRouter(prefix="/api/v1/account")


def set_account_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        "teamnav_account",
        token,
        max_age=settings.account_session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: AccountCredentials,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    try:
        user, token, csrf = await AccountAuth(session, settings).register(data.email, data.password)
    except AccountConflictError as error:
        raise HTTPException(status_code=409, detail={"code": "EMAIL_ALREADY_REGISTERED"}) from error
    set_account_cookie(response, token, settings)
    return {"email": user.email, "csrf_token": csrf}


@router.post("/login")
async def login(
    data: AccountCredentials,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    try:
        user, token, csrf = await AccountAuth(session, settings).login(data.email, data.password)
    except AccountAuthenticationError as error:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS"}) from error
    set_account_cookie(response, token, settings)
    return {"email": user.email, "csrf_token": csrf}


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    await AccountAuth(session, settings).logout(request.cookies.get("teamnav_account"))
    response.delete_cookie("teamnav_account", path="/api/v1")


@router.get("/sites")
async def account_sites(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    try:
        user, _ = await AccountAuth(session, settings).authenticate(
            request.cookies.get("teamnav_account")
        )
    except AccountAuthenticationError as error:
        raise HTTPException(status_code=401, detail={"code": "ACCOUNT_SESSION_REQUIRED"}) from error
    sites = list(
        (
            await session.scalars(
                select(Site)
                .where(Site.owner_id == user.id, Site.deleted_at.is_(None))
                .order_by(Site.created_at.desc())
            )
        ).all()
    )
    return {
        "email": user.email,
        "sites": [
            {
                "public_slug": site.public_slug,
                "name": site.name,
                "description": site.description,
                "icon": site.icon,
                "theme": site.theme,
                "visit_count": site.visit_count,
                "is_disabled": site.is_disabled,
                "updated_at": site.updated_at.isoformat(),
            }
            for site in sites
        ],
    }
