from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import settings_from_request
from app.api.sites import get_session
from app.core.config import Settings
from app.core.security import generate_token, hash_password, token_digest
from app.models import AccessSession, Site
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
    MaintenanceBulkRequest,
    MaintenanceCheckRequest,
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
from app.services.maintenance import LinkMaintenanceService
from app.services.manage import (
    BatchLinkValidationError,
    ResourceNotFoundError,
    SiteImportValidationError,
    SiteLimitError,
    SiteManager,
    category_payload,
    link_payload,
)
from app.services.metrics import MetricsRecorder
from app.services.revisions import RevisionNotFoundError, RevisionService
from app.services.sites import SiteDisabledError, SiteNotFoundError, SiteService

router = APIRouter(prefix="/api/v1/manage/sites")


def revision_action(request: Request, slug: str) -> str | None:
    if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return None
    prefix = f"/api/v1/manage/sites/{slug}"
    tail = request.url.path.removeprefix(prefix)
    if tail in {
        "/clone",
        "/claim",
        "/maintenance/check",
        "/rotate-edit-key",
    } or tail.endswith("/restore"):
        return None
    if tail == "" and request.method == "PATCH":
        return "site_updated"
    if tail == "/categories" and request.method == "POST":
        return "category_created"
    if tail == "/categories/reorder":
        return "categories_reordered"
    if tail.startswith("/categories/"):
        return "category_deleted" if request.method == "DELETE" else "category_updated"
    if tail == "/links" and request.method == "POST":
        return "link_created"
    if tail == "/links/batch":
        return "links_batch_created"
    if tail in {"/links/reorder", "/links/organize"}:
        return "links_reordered"
    if tail.startswith("/links/"):
        return "link_deleted" if request.method == "DELETE" else "link_updated"
    if tail == "/bookmarks/import":
        return "bookmarks_imported"
    if tail == "/import":
        return "site_imported"
    if tail == "/maintenance/bulk":
        return "links_maintained"
    return None


async def authorized_site(
    slug: str,
    request: Request,
    session: AsyncSession,
    settings: Settings,
    *,
    mutation: bool,
):
    async def finish(site: Site) -> Site:
        if mutation and (action := revision_action(request, slug)):
            await RevisionService(session).capture(site.id, action)
        return site

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
            return await finish(site)
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
        return await finish(site)
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
    except BatchLinkValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": str(error), "line": error.line_number},
        ) from error


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
) -> dict[str, Any]:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    inspection = BookmarkCodec.inspect(data.html)
    if not inspection.categories:
        raise HTTPException(
            status_code=422,
            detail={"code": "BOOKMARK_FILE_NO_SUPPORTED_LINKS"},
        )
    manager = SiteManager(session, settings, site)
    plan = await manager.plan_bookmark_import(
        inspection.categories,
        mode=data.mode,
        duplicate_strategy=data.duplicate_strategy,
        source_categories=inspection.source_categories,
        source_links=inspection.source_links,
        unsupported_links=inspection.unsupported_links,
    )
    try:
        result = await manager.import_bookmarks(plan)
        result["imported_categories"] = plan.created_categories
        return result
    except SiteLimitError as error:
        raise management_error(error) from error


@router.post("/{slug}/bookmarks/preview")
async def preview_bookmarks(
    slug: str,
    data: BookmarkImport,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, Any]:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    inspection = BookmarkCodec.inspect(data.html)
    if not inspection.categories:
        raise HTTPException(
            status_code=422,
            detail={"code": "BOOKMARK_FILE_NO_SUPPORTED_LINKS"},
        )
    plan = await SiteManager(session, settings, site).plan_bookmark_import(
        inspection.categories,
        mode=data.mode,
        duplicate_strategy=data.duplicate_strategy,
        source_categories=inspection.source_categories,
        source_links=inspection.source_links,
        unsupported_links=inspection.unsupported_links,
    )
    return plan.payload()


@router.get("/{slug}/maintenance")
async def maintenance_report(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, Any]:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    return await LinkMaintenanceService(session, settings).report(site.id)


@router.post("/{slug}/maintenance/check")
async def check_links(
    slug: str,
    data: MaintenanceCheckRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, Any]:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    return await LinkMaintenanceService(session, settings).check_site(
        site,
        force=True,
        limit=data.limit,
    )


@router.post("/{slug}/maintenance/bulk")
async def bulk_maintain_links(
    slug: str,
    data: MaintenanceBulkRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, int]:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        updated = await LinkMaintenanceService(session, settings).bulk(site.id, data.action)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": str(error)},
        ) from error
    return {"updated": updated}


@router.get("/{slug}/revisions")
async def list_revisions(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> list[dict[str, Any]]:
    site = await authorized_site(slug, request, session, settings, mutation=False)
    return await RevisionService(session).list(site.id)


@router.post("/{slug}/revisions/{revision_id}/restore")
async def restore_revision(
    slug: str,
    revision_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_from_request),
) -> dict[str, Any]:
    site = await authorized_site(slug, request, session, settings, mutation=True)
    try:
        await RevisionService(session).restore(site.id, revision_id)
    except RevisionNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": str(error)}) from error
    session.expire_all()
    loaded = await SiteService(session, settings).get_site(slug)
    return SiteService.serialize(loaded, public=False)


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
    try:
        await SiteManager(session, settings, site).import_site_data(data.data, data.mode)
    except SiteImportValidationError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error
    except SiteLimitError as error:
        raise management_error(error) from error
    session.expire_all()
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
