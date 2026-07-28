from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import settings_from_request
from app.api.sites import get_session
from app.core.config import Settings
from app.core.security import generate_token, hash_password, token_digest
from app.models import AccessSession, Category, Site
from app.schemas import (
    BatchLinks,
    BookmarkImport,
    CategoryCreate,
    CategoryUpdate,
    CloneSite,
    DeleteSite,
    ImportRequest,
    LinkCreate,
    LinkOrganizeItem,
    LinkUpdate,
    ReorderItem,
    SessionCreate,
    SiteUpdate,
)
from app.services.account_auth import (
    AccountAuth,
    AccountAuthenticationError,
    AccountAuthorizationError,
)
from app.services.auth import AuthenticationError, AuthorizationError, ManageAuth
from app.services.bookmarks import BookmarkCodec
from app.services.manage import (
    ResourceNotFoundError,
    SiteLimitError,
    SiteManager,
    category_payload,
    link_payload,
)
from app.services.metrics import MetricsRecorder
from app.services.sites import SiteDisabledError, SiteNotFoundError, SiteService

router = APIRouter(prefix="/api/v1/manage/sites")


async def authorized_site(
    slug: str,
    request: Request,
    session: AsyncSession,
    settings: Settings,
    *,
    mutation: bool,
):
    auth = ManageAuth(session, settings)
    manage_authenticated = False
    try:
        site, manage_session = await auth.authenticate(slug, request.cookies.get("teamnav_manage"))
        manage_authenticated = True
    except AuthenticationError:
        pass
    else:
        if not mutation:
            return site
        try:
            auth.check_csrf(manage_session, request.headers.get("X-CSRF-Token"))
            return site
        except AuthorizationError:
            pass

    try:
        account = AccountAuth(session, settings)
        user, user_session = await account.authenticate(request.cookies.get("teamnav_account"))
        site = await session.scalar(
            select(Site).where(
                Site.public_slug == slug,
                Site.owner_id == user.id,
                Site.deleted_at.is_(None),
                Site.is_disabled.is_(False),
            )
        )
        if site is None:
            raise AccountAuthenticationError
        if mutation:
            account.check_csrf(user_session, request.headers.get("X-CSRF-Token"))
        return site
    except AccountAuthenticationError as error:
        code = "CSRF_FAILED" if manage_authenticated else "MANAGE_SESSION_REQUIRED"
        status_code = 403 if manage_authenticated else 401
        raise HTTPException(status_code=status_code, detail={"code": code}) from error
    except AccountAuthorizationError as error:
        raise HTTPException(status_code=403, detail={"code": "CSRF_FAILED"}) from error


def management_error(error: Exception) -> HTTPException:
    if isinstance(error, ResourceNotFoundError):
        return HTTPException(status_code=404, detail={"code": str(error)})
    if isinstance(error, SiteLimitError):
        return HTTPException(status_code=409, detail=error.detail)
    return HTTPException(status_code=409, detail={"code": str(error)})


@router.post("/{slug}/session")
async def create_manage_session(
    slug: str,
    data: SessionCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    service = SiteService(session, settings)
    try:
        site = await service.get_site(slug)
        session_token, csrf_token = await ManageAuth(session, settings).exchange_key(
            site, data.edit_key
        )
    except (SiteNotFoundError, SiteDisabledError, AuthenticationError) as error:
        raise HTTPException(status_code=401, detail={"code": "INVALID_EDIT_KEY"}) from error
    response.set_cookie(
        "teamnav_manage",
        session_token,
        max_age=settings.edit_session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/manage",
    )
    return {"site": service.serialize(site, public=False), "csrf_token": csrf_token}


@router.get("/{slug}")
async def get_managed_site(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    loaded = await SiteService(session, settings).get_site(site.public_slug)
    return SiteService.serialize(loaded, public=False)


@router.patch("/{slug}")
async def update_site(
    slug: str,
    data: SiteUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    changes = data.model_dump(exclude_unset=True)
    display_keys = {
        "show_search",
        "show_updated_at",
        "show_visit_count",
        "show_descriptions",
        "show_tags",
    }
    display_config = dict(site.display_config)
    for key in display_keys:
        if key in changes:
            display_config[key] = changes.pop(key)
    site.display_config = display_config
    if "access_password" in changes:
        password = changes.pop("access_password")
        site.access_password_hash = hash_password(password) if password else None
        site.password_version += 1
        await session.execute(delete(AccessSession).where(AccessSession.site_id == site.id))
    for field, value in changes.items():
        setattr(site, field, value)
    await session.commit()
    loaded = await SiteService(session, settings).get_site(slug)
    return SiteService.serialize(loaded, public=False)


@router.post("/{slug}/rotate-edit-key")
async def rotate_edit_key(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    new_key = generate_token()
    site.edit_key_hash = token_digest(new_key, settings.secret_key)
    await ManageAuth(session, settings).revoke_all(site.id)
    await session.commit()
    manage_url = f"{settings.app_url}/manage/{slug}?key={new_key}"
    return {
        "manage_url": manage_url,
        "recovery_payload": {"version": 1, "public_slug": slug, "edit_key": new_key},
    }


@router.post("/{slug}/categories", status_code=201)
async def create_category(
    slug: str,
    data: CategoryCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        return category_payload(await SiteManager(session, settings, site).create_category(data))
    except (ResourceNotFoundError, SiteLimitError) as error:
        raise management_error(error) from error


@router.patch("/{slug}/categories/{category_id}")
async def update_category(
    slug: str,
    category_id: str,
    data: CategoryUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        item = await SiteManager(session, settings, site).update_category(category_id, data)
        return category_payload(item)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.delete("/{slug}/categories/{category_id}", status_code=204)
async def delete_category(
    slug: str,
    category_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        await SiteManager(session, settings, site).delete_category(category_id)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.put("/{slug}/categories/reorder", status_code=204)
async def reorder_categories(
    slug: str,
    items: list[ReorderItem],
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        await SiteManager(session, settings, site).reorder_categories(items)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.post("/{slug}/links", status_code=201)
async def create_link(
    slug: str,
    data: LinkCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        return link_payload(await SiteManager(session, settings, site).create_link(data))
    except (ResourceNotFoundError, SiteLimitError) as error:
        raise management_error(error) from error


@router.put("/{slug}/links/organize", status_code=204)
async def organize_links(
    slug: str,
    items: list[LinkOrganizeItem],
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        await SiteManager(session, settings, site).organize_links(items)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.patch("/{slug}/links/{link_id}")
async def update_link(
    slug: str,
    link_id: str,
    data: LinkUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        item = await SiteManager(session, settings, site).update_link(link_id, data)
        return link_payload(item)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.delete("/{slug}/links/{link_id}", status_code=204)
async def delete_link(
    slug: str,
    link_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        await SiteManager(session, settings, site).delete_link(link_id)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.put("/{slug}/links/reorder", status_code=204)
async def reorder_links(
    slug: str,
    items: list[ReorderItem],
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        await SiteManager(session, settings, site).reorder_links(items)
    except ResourceNotFoundError as error:
        raise management_error(error) from error


@router.post("/{slug}/links/batch", status_code=201)
async def batch_links(
    slug: str,
    data: BatchLinks,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> list[dict]:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        items = await SiteManager(session, settings, site).batch_links(data.category_id, data.lines)
        return [link_payload(item) for item in items]
    except (ResourceNotFoundError, SiteLimitError) as error:
        raise management_error(error) from error


@router.get("/{slug}/export")
async def export_site(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    loaded = await SiteService(session, settings).get_site(site.public_slug)
    payload = SiteService.serialize(loaded, public=False)
    payload["version"] = 1
    payload.pop("visit_count", None)
    payload.pop("public_slug", None)
    return payload


@router.get("/{slug}/bookmarks/export", response_class=PlainTextResponse)
async def export_bookmarks(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> PlainTextResponse:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    loaded = await SiteService(session, settings).get_site(site.public_slug)
    return PlainTextResponse(
        BookmarkCodec.export(loaded.name, loaded.categories),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="teamnav-{slug}-bookmarks.html"'},
    )


@router.post("/{slug}/bookmarks/import")
async def import_bookmarks(
    slug: str,
    data: BookmarkImport,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, int]:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    categories = BookmarkCodec.parse(data.html)
    manager = SiteManager(session, settings, site)
    try:
        imported_categories, imported_links = await manager.import_bookmarks(
            categories, data.mode
        )
    except SiteLimitError as error:
        raise management_error(error) from error
    return {
        "imported_categories": imported_categories,
        "imported_links": imported_links,
    }


@router.post("/{slug}/clone", status_code=201)
async def clone_site(
    slug: str,
    data: CloneSite,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    loaded = await SiteService(session, settings).get_site(site.public_slug)
    return await SiteService(session, settings).clone(loaded, data.name)


@router.post("/{slug}/claim")
async def claim_site(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        user, _ = await AccountAuth(session, settings).authenticate(
            request.cookies.get("teamnav_account")
        )
    except AccountAuthenticationError as error:
        raise HTTPException(status_code=401, detail={"code": "ACCOUNT_SESSION_REQUIRED"}) from error
    if site.owner_id and site.owner_id != user.id:
        raise HTTPException(status_code=409, detail={"code": "SITE_ALREADY_OWNED"})
    site.owner_id = user.id
    await session.commit()
    return {"public_slug": site.public_slug, "owner_email": user.email}


@router.get("/{slug}/stats")
async def site_stats(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    return await MetricsRecorder(session).report(site.id)


@router.post("/{slug}/import")
async def import_site(
    slug: str,
    data: ImportRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    if data.mode == "replace":
        await session.execute(delete(Category).where(Category.site_id == site.id))
        await session.flush()
    manager = SiteManager(session, settings, site)
    for category_data in data.data.get("categories", []):
        category = await manager.create_category(
            CategoryCreate(
                name=category_data.get("name", "未命名分类"),
                description=category_data.get("description"),
                icon=category_data.get("icon", "📁"),
                is_visible=category_data.get("is_visible", True),
            )
        )
        for link_data in category_data.get("links", []):
            await manager.create_link(
                LinkCreate(
                    category_id=category.id,
                    name=link_data.get("name", "未命名链接"),
                    url=link_data.get("url", ""),
                    description=link_data.get("description"),
                    icon=link_data.get("icon", "🔗"),
                    tags=link_data.get("tags", []),
                    is_pinned=link_data.get("is_pinned", False),
                    is_enabled=link_data.get("is_enabled", True),
                    open_mode=link_data.get("open_mode", "new"),
                )
            )
    loaded = await SiteService(session, settings).get_site(slug)
    return SiteService.serialize(loaded, public=False)


@router.delete("/{slug}", status_code=204)
async def delete_site(
    slug: str,
    data: DeleteSite,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> None:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    if data.confirm_name != site.name:
        raise HTTPException(status_code=409, detail={"code": "CONFIRM_NAME_MISMATCH"})
    site.deleted_at = datetime.now(UTC)
    await ManageAuth(session, settings).revoke_all(site.id)
    await session.commit()
