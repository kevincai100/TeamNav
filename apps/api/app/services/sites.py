import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.security import generate_slug, generate_token, hash_password, token_digest
from app.models import Category, CreateAttempt, Link, Site
from app.schemas import SiteCreate


class SiteNotFoundError(Exception):
    pass


class SiteDisabledError(Exception):
    pass


class RateLimitError(Exception):
    pass


class SiteService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def create(self, data: SiteCreate, creator_ip: str) -> dict[str, Any]:
        ip_hash = token_digest(creator_ip, self.settings.secret_key)
        await self._check_rate_limit(ip_hash)
        template = self._load_template(data.template_id)
        edit_key = generate_token()
        site = Site(
            public_slug=generate_slug(),
            name=data.name,
            description=data.description,
            icon=data.icon,
            theme=data.theme,
            edit_key_hash=token_digest(edit_key, self.settings.secret_key),
            access_password_hash=(
                hash_password(data.access_password) if data.access_password else None
            ),
            allow_indexing=not self.settings.default_noindex,
            display_config={
                "show_search": True,
                "show_updated_at": True,
                "show_visit_count": False,
            },
        )
        self.session.add(site)
        self.session.add(CreateAttempt(ip_hash=ip_hash))
        await self.session.flush()
        self._apply_template(site, template)
        await self.session.commit()

        public_url = f"{self.settings.app_url}/s/{site.public_slug}"
        manage_url = f"{self.settings.app_url}/manage/{site.public_slug}?key={edit_key}"
        return {
            "site": {"public_slug": site.public_slug, "name": site.name},
            "public_url": public_url,
            "manage_url": manage_url,
            "recovery_payload": {
                "version": 1,
                "public_slug": site.public_slug,
                "edit_key": edit_key,
            },
        }

    async def _check_rate_limit(self, ip_hash: str) -> None:
        current = datetime.now(UTC)
        hour_count = await self.session.scalar(
            select(func.count())
            .select_from(CreateAttempt)
            .where(
                CreateAttempt.ip_hash == ip_hash,
                CreateAttempt.created_at >= current - timedelta(hours=1),
            )
        )
        day_count = await self.session.scalar(
            select(func.count())
            .select_from(CreateAttempt)
            .where(
                CreateAttempt.ip_hash == ip_hash,
                CreateAttempt.created_at >= current - timedelta(days=1),
            )
        )
        if (hour_count or 0) >= self.settings.max_sites_per_ip_per_hour or (
            day_count or 0
        ) >= self.settings.max_sites_per_ip_per_day:
            raise RateLimitError

    async def get_site(self, slug: str) -> Site:
        result = await self.session.execute(
            select(Site)
            .where(Site.public_slug == slug, Site.deleted_at.is_(None))
            .options(selectinload(Site.categories).selectinload(Category.links))
        )
        site = result.scalar_one_or_none()
        if site is None:
            raise SiteNotFoundError
        if site.is_disabled:
            raise SiteDisabledError
        return site

    @staticmethod
    def serialize(site: Site, *, public: bool) -> dict[str, Any]:
        categories = []
        for category in sorted(site.categories, key=lambda item: item.sort_order):
            if public and not category.is_visible:
                continue
            links = []
            for link in sorted(
                category.links, key=lambda item: (not item.is_pinned, item.sort_order)
            ):
                if public and not link.is_enabled:
                    continue
                links.append(
                    {
                        "id": link.id,
                        "name": link.name,
                        "url": link.url,
                        "description": link.description,
                        "icon": link.icon,
                        "tags": link.tags,
                        "sort_order": link.sort_order,
                        "is_pinned": link.is_pinned,
                        "is_enabled": link.is_enabled,
                        "open_mode": link.open_mode,
                        "category_id": category.id,
                    }
                )
            categories.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "icon": category.icon,
                    "sort_order": category.sort_order,
                    "is_visible": category.is_visible,
                    "links": links,
                }
            )
        return {
            "public_slug": site.public_slug,
            "name": site.name,
            "description": site.description,
            "icon": site.icon,
            "theme": site.theme,
            "allow_indexing": site.allow_indexing,
            "password_protected": bool(site.access_password_hash),
            "display_config": site.display_config,
            "visit_count": site.visit_count,
            "updated_at": site.updated_at.isoformat(),
            "categories": categories,
        }

    @staticmethod
    def _load_template(template_id: str) -> dict[str, Any]:
        if not template_id.replace("-", "").isalnum():
            raise ValueError("INVALID_TEMPLATE")
        root = Path(__file__).parents[4] / "packages" / "templates"
        path = root / f"{template_id}.json"
        if not path.exists():
            raise ValueError("TEMPLATE_NOT_FOUND")
        return json.loads(path.read_text(encoding="utf-8"))

    def _apply_template(self, site: Site, template: dict[str, Any]) -> None:
        for category_order, category_data in enumerate(template.get("categories", [])):
            category = Category(
                site=site,
                name=category_data["name"][:50],
                description=category_data.get("description"),
                icon=category_data.get("icon", "📁"),
                sort_order=category_order,
            )
            self.session.add(category)
            for link_order, link_data in enumerate(category_data.get("links", [])):
                self.session.add(
                    Link(
                        site_id=site.id,
                        category=category,
                        name=link_data["name"][:100],
                        url=link_data["url"],
                        description=link_data.get("description"),
                        icon=link_data.get("icon", "🔗"),
                        tags=link_data.get("tags", []),
                        sort_order=link_order,
                    )
                )
