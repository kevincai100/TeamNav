from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Link, Site, SiteRevision

REVISION_LIMIT = 20


class RevisionNotFoundError(Exception):
    pass


def _link_snapshot(link: Link) -> dict[str, Any]:
    return {
        "name": link.name,
        "url": link.url,
        "description": link.description,
        "icon": link.icon,
        "tags": list(link.tags),
        "sort_order": link.sort_order,
        "is_pinned": link.is_pinned,
        "is_enabled": link.is_enabled,
        "open_mode": link.open_mode,
        "health_status": link.health_status,
        "health_status_code": link.health_status_code,
        "health_error": link.health_error,
        "health_checked_at": (
            link.health_checked_at.isoformat() if link.health_checked_at else None
        ),
        "health_consecutive_failures": link.health_consecutive_failures,
    }


def _site_snapshot(site: Site) -> dict[str, Any]:
    return {
        "name": site.name,
        "description": site.description,
        "icon": site.icon,
        "theme": site.theme,
        "allow_indexing": site.allow_indexing,
        "layout_config": dict(site.layout_config),
        "display_config": dict(site.display_config),
        "maintenance_config": dict(site.maintenance_config or {}),
        "categories": [
            {
                "name": category.name,
                "description": category.description,
                "icon": category.icon,
                "sort_order": category.sort_order,
                "is_visible": category.is_visible,
                "links": [
                    _link_snapshot(link)
                    for link in sorted(category.links, key=lambda item: item.sort_order)
                ],
            }
            for category in sorted(site.categories, key=lambda item: item.sort_order)
        ],
    }


class RevisionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def capture(self, site_id: str, action: str) -> SiteRevision:
        site = await self._site(site_id)
        revision = SiteRevision(
            site_id=site.id,
            action=action,
            snapshot=_site_snapshot(site),
        )
        self.session.add(revision)
        await self.session.flush()
        revision_ids = list(
            (
                await self.session.scalars(
                    select(SiteRevision.id)
                    .where(SiteRevision.site_id == site_id)
                    .order_by(SiteRevision.created_at.desc(), SiteRevision.id.desc())
                )
            ).all()
        )
        stale = revision_ids[REVISION_LIMIT:]
        if stale:
            await self.session.execute(delete(SiteRevision).where(SiteRevision.id.in_(stale)))
        return revision

    async def list(self, site_id: str) -> list[dict[str, Any]]:
        revisions = list(
            (
                await self.session.scalars(
                    select(SiteRevision)
                    .where(SiteRevision.site_id == site_id)
                    .order_by(SiteRevision.created_at.desc(), SiteRevision.id.desc())
                    .limit(REVISION_LIMIT)
                )
            ).all()
        )
        return [self._payload(revision) for revision in revisions]

    async def restore(self, site_id: str, revision_id: str) -> None:
        revision = await self.session.scalar(
            select(SiteRevision).where(
                SiteRevision.id == revision_id,
                SiteRevision.site_id == site_id,
            )
        )
        if revision is None:
            raise RevisionNotFoundError("REVISION_NOT_FOUND")
        snapshot = revision.snapshot
        await self.capture(site_id, "revision_restored")
        site = await self._site(site_id)
        await self.session.execute(delete(Category).where(Category.site_id == site_id))
        await self.session.flush()
        for field in (
            "name",
            "description",
            "icon",
            "theme",
            "allow_indexing",
            "layout_config",
            "display_config",
            "maintenance_config",
        ):
            if field in snapshot:
                setattr(site, field, snapshot[field])
        for category_data in snapshot.get("categories", []):
            category = Category(
                site_id=site_id,
                name=category_data["name"],
                description=category_data.get("description"),
                icon=category_data.get("icon", "📁"),
                sort_order=category_data.get("sort_order", 0),
                is_visible=category_data.get("is_visible", True),
            )
            self.session.add(category)
            await self.session.flush()
            for link_data in category_data.get("links", []):
                self.session.add(
                    Link(
                        site_id=site_id,
                        category_id=category.id,
                        name=link_data["name"],
                        url=link_data["url"],
                        description=link_data.get("description"),
                        icon=link_data.get("icon", "🔗"),
                        tags=list(link_data.get("tags", [])),
                        sort_order=link_data.get("sort_order", 0),
                        is_pinned=link_data.get("is_pinned", False),
                        is_enabled=link_data.get("is_enabled", True),
                        open_mode=link_data.get("open_mode", "new"),
                        health_status=link_data.get("health_status", "unchecked"),
                        health_status_code=link_data.get("health_status_code"),
                        health_error=link_data.get("health_error"),
                        health_checked_at=(
                            datetime.fromisoformat(link_data["health_checked_at"])
                            if link_data.get("health_checked_at")
                            else None
                        ),
                        health_consecutive_failures=link_data.get(
                            "health_consecutive_failures", 0
                        ),
                    )
                )
        await self.session.commit()

    async def _site(self, site_id: str) -> Site:
        site = await self.session.scalar(
            select(Site)
            .where(Site.id == site_id)
            .options(selectinload(Site.categories).selectinload(Category.links))
            .execution_options(populate_existing=True)
        )
        if site is None:
            raise RevisionNotFoundError("SITE_NOT_FOUND")
        return site

    @staticmethod
    def _payload(revision: SiteRevision) -> dict[str, Any]:
        categories = revision.snapshot.get("categories", [])
        return {
            "id": revision.id,
            "action": revision.action,
            "created_at": revision.created_at.isoformat(),
            "category_count": len(categories),
            "link_count": sum(len(category.get("links", [])) for category in categories),
        }
