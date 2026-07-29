from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Category, Link, Site
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    LinkCreate,
    LinkOrganizeItem,
    LinkUpdate,
    ReorderItem,
)
from app.services.bookmarks import BookmarkCategory, BookmarkLink


@dataclass
class PlannedBookmarkCategory:
    name: str
    source_links: int = 0
    links: list[BookmarkLink] = dataclass_field(default_factory=list)
    existing_id: str | None = None


@dataclass
class BookmarkImportPlan:
    mode: Literal["replace", "merge"]
    duplicate_strategy: Literal["skip", "keep"]
    source_categories: int
    source_links: int
    accepted_links: int
    unsupported_links: int
    duplicate_links: int
    categories: list[PlannedBookmarkCategory]
    current_categories: int
    current_links: int
    max_categories: int
    max_links: int

    @property
    def imported_links(self) -> int:
        return sum(len(category.links) for category in self.categories)

    @property
    def created_categories(self) -> int:
        return sum(category.existing_id is None for category in self.categories)

    @property
    def matched_categories(self) -> int:
        return sum(category.existing_id is not None for category in self.categories)

    def payload(self) -> dict[str, Any]:
        categories_after = self.current_categories + self.created_categories
        links_after = self.current_links + self.imported_links
        categories_allowed = categories_after <= self.max_categories
        links_allowed = links_after <= self.max_links
        return {
            "mode": self.mode,
            "duplicate_strategy": self.duplicate_strategy,
            "source_categories": self.source_categories,
            "source_links": self.source_links,
            "accepted_links": self.accepted_links,
            "unsupported_links": self.unsupported_links,
            "duplicate_links": self.duplicate_links,
            "imported_links": self.imported_links,
            "created_categories": self.created_categories,
            "matched_categories": self.matched_categories,
            "capacity": {
                "allowed": categories_allowed and links_allowed,
                "categories": {
                    "current": self.current_categories,
                    "importing": self.created_categories,
                    "after": categories_after,
                    "limit": self.max_categories,
                    "allowed": categories_allowed,
                },
                "links": {
                    "current": self.current_links,
                    "importing": self.imported_links,
                    "after": links_after,
                    "limit": self.max_links,
                    "allowed": links_allowed,
                },
            },
            "categories": [
                {
                    "name": category.name,
                    "source_links": category.source_links,
                    "imported_links": len(category.links),
                    "existing": category.existing_id is not None,
                }
                for category in self.categories
            ],
        }


def normalize_bookmark_url(value: str) -> str:
    raw_value = value.strip()
    try:
        parsed = urlsplit(raw_value)
        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return raw_value
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    if ":" in hostname:
        hostname = f"[{hostname}]"
    userinfo, separator, _ = parsed.netloc.rpartition("@")
    authority = f"{userinfo}{separator}" if separator else ""
    netloc = f"{authority}{hostname}"
    if port is not None:
        netloc = f"{netloc}:{port}"
    path = parsed.path or ("/" if scheme in {"http", "https"} else "")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


class ResourceNotFoundError(Exception):
    pass


class SiteLimitError(Exception):
    def __init__(
        self,
        code: str,
        *,
        current: int | None = None,
        importing: int | None = None,
        limit: int | None = None,
    ) -> None:
        super().__init__(code)
        self.detail: dict[str, int | str] = {"code": code}
        if current is not None:
            self.detail.update(current=current, importing=importing or 0, limit=limit or 0)


class BatchLinkValidationError(Exception):
    def __init__(self, line_number: int) -> None:
        super().__init__("BATCH_LINK_INVALID")
        self.line_number = line_number


class SiteImportValidationError(Exception):
    pass


class SiteManager:
    def __init__(self, session: AsyncSession, settings: Settings, site: Site) -> None:
        self.session = session
        self.settings = settings
        self.site = site

    async def create_category(self, data: CategoryCreate) -> Category:
        count = await self.session.scalar(
            select(func.count()).select_from(Category).where(Category.site_id == self.site.id)
        )
        if (count or 0) >= self.settings.max_categories_per_site:
            raise SiteLimitError("CATEGORY_LIMIT_REACHED")
        last_order = await self.session.scalar(
            select(func.max(Category.sort_order)).where(Category.site_id == self.site.id)
        )
        category = Category(
            site_id=self.site.id,
            sort_order=(last_order if last_order is not None else -1) + 1,
            **data.model_dump(),
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def update_category(self, category_id: str, data: CategoryUpdate) -> Category:
        category = await self._category(category_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
        await self.session.commit()
        return category

    async def delete_category(self, category_id: str) -> None:
        category = await self._category(category_id)
        await self.session.delete(category)
        await self.session.commit()

    async def reorder_categories(self, items: list[ReorderItem]) -> None:
        categories = {item.id: await self._category(item.id) for item in items}
        for item in items:
            categories[item.id].sort_order = item.sort_order
        await self.session.commit()

    async def create_link(self, data: LinkCreate) -> Link:
        await self._category(data.category_id)
        count = await self.session.scalar(
            select(func.count()).select_from(Link).where(Link.site_id == self.site.id)
        )
        if (count or 0) >= self.settings.max_links_per_site:
            raise SiteLimitError("LINK_LIMIT_REACHED")
        last_order = await self.session.scalar(
            select(func.max(Link.sort_order)).where(Link.category_id == data.category_id)
        )
        link = Link(
            site_id=self.site.id,
            sort_order=(last_order if last_order is not None else -1) + 1,
            **data.model_dump(),
        )
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def update_link(self, link_id: str, data: LinkUpdate) -> Link:
        link = await self._link(link_id)
        changes = data.model_dump(exclude_unset=True)
        if "category_id" in changes:
            await self._category(changes["category_id"])
        for field, value in changes.items():
            setattr(link, field, value)
        await self.session.commit()
        return link

    async def delete_link(self, link_id: str) -> None:
        link = await self._link(link_id)
        await self.session.delete(link)
        await self.session.commit()

    async def reorder_links(self, items: list[ReorderItem]) -> None:
        links = {item.id: await self._link(item.id) for item in items}
        for item in items:
            links[item.id].sort_order = item.sort_order
        await self.session.commit()

    async def organize_links(self, items: list[LinkOrganizeItem]) -> None:
        categories = {
            item.category_id: await self._category(item.category_id) for item in items
        }
        links = {item.id: await self._link(item.id) for item in items}
        for item in items:
            links[item.id].category = categories[item.category_id]
            links[item.id].sort_order = item.sort_order
        await self.session.commit()

    async def batch_links(self, category_id: str, lines: str) -> list[Link]:
        await self._category(category_id)
        parsed: list[LinkCreate] = []
        for line_number, raw_line in enumerate(lines.splitlines(), start=1):
            parts = [part.strip() for part in raw_line.split("|")]
            if len(parts) < 2 or not parts[0] or not parts[1]:
                continue
            try:
                parsed.append(
                    LinkCreate(
                        category_id=category_id,
                        name=parts[0],
                        url=parts[1],
                        description=parts[2] if len(parts) > 2 else None,
                        tags=(
                            [tag.strip() for tag in parts[3].split(",") if tag.strip()][:10]
                            if len(parts) > 3
                            else []
                        ),
                    )
                )
            except ValidationError as error:
                raise BatchLinkValidationError(line_number) from error
        current = (
            await self.session.scalar(
                select(func.count()).select_from(Link).where(Link.site_id == self.site.id)
            )
            or 0
        )
        if current + len(parsed) > self.settings.max_links_per_site:
            raise SiteLimitError(
                "LINK_LIMIT_REACHED",
                current=current,
                importing=len(parsed),
                limit=self.settings.max_links_per_site,
            )
        last_order_value = await self.session.scalar(
            select(func.max(Link.sort_order)).where(Link.category_id == category_id)
        )
        last_order = last_order_value if last_order_value is not None else -1
        created = [
            Link(
                site_id=self.site.id,
                sort_order=last_order + offset,
                **item.model_dump(),
            )
            for offset, item in enumerate(parsed, start=1)
        ]
        self.session.add_all(created)
        await self.session.commit()
        return created

    async def import_bookmarks(
        self,
        plan: BookmarkImportPlan,
    ) -> dict[str, Any]:
        if plan.current_categories + plan.created_categories > plan.max_categories:
            raise SiteLimitError(
                "BOOKMARK_IMPORT_CATEGORY_LIMIT_REACHED",
                current=plan.current_categories,
                importing=plan.created_categories,
                limit=plan.max_categories,
            )
        if plan.current_links + plan.imported_links > plan.max_links:
            raise SiteLimitError(
                "BOOKMARK_IMPORT_LINK_LIMIT_REACHED",
                current=plan.current_links,
                importing=plan.imported_links,
                limit=plan.max_links,
            )

        if plan.mode == "replace":
            await self.session.execute(delete(Category).where(Category.site_id == self.site.id))
            await self.session.flush()
        last_category_order_value = await self.session.scalar(
            select(func.max(Category.sort_order)).where(Category.site_id == self.site.id)
        )
        last_category_order = (
            last_category_order_value if last_category_order_value is not None else -1
        )
        created_offset = 0
        for category_data in plan.categories:
            category = (
                await self.session.get(Category, category_data.existing_id)
                if category_data.existing_id
                else None
            )
            if category is None:
                created_offset += 1
                category = Category(
                    site_id=self.site.id,
                    name=category_data.name,
                    sort_order=last_category_order + created_offset,
                )
                self.session.add(category)
                await self.session.flush()
                last_link_order = -1
            else:
                last_link_order_value = await self.session.scalar(
                    select(func.max(Link.sort_order)).where(Link.category_id == category.id)
                )
                last_link_order = (
                    last_link_order_value if last_link_order_value is not None else -1
                )
            for link_offset, link_data in enumerate(category_data.links, start=1):
                self.session.add(
                    Link(
                        site_id=self.site.id,
                        category_id=category.id,
                        name=link_data.name,
                        url=link_data.url,
                        tags=link_data.tags,
                        sort_order=last_link_order + link_offset,
                    )
                )
        await self.session.commit()
        return plan.payload()

    async def import_site_data(
        self,
        data: dict[str, Any],
        mode: Literal["replace", "merge"],
    ) -> None:
        raw_categories = data.get("categories", [])
        if not isinstance(raw_categories, list):
            raise SiteImportValidationError("SITE_IMPORT_INVALID")
        planned: list[tuple[CategoryCreate, list[LinkCreate]]] = []
        try:
            for category_data in raw_categories:
                if not isinstance(category_data, dict):
                    raise SiteImportValidationError("SITE_IMPORT_INVALID")
                category = CategoryCreate(
                    name=category_data.get("name", "未命名分类"),
                    description=category_data.get("description"),
                    icon=category_data.get("icon", "📁"),
                    is_visible=category_data.get("is_visible", True),
                )
                raw_links = category_data.get("links", [])
                if not isinstance(raw_links, list):
                    raise SiteImportValidationError("SITE_IMPORT_INVALID")
                links = [
                    LinkCreate(
                        category_id="pending",
                        name=link_data.get("name", "未命名链接"),
                        url=link_data.get("url", ""),
                        description=link_data.get("description"),
                        icon=link_data.get("icon", "🔗"),
                        tags=link_data.get("tags", []),
                        is_pinned=link_data.get("is_pinned", False),
                        is_enabled=link_data.get("is_enabled", True),
                        open_mode=link_data.get("open_mode", "new"),
                    )
                    for link_data in raw_links
                    if isinstance(link_data, dict)
                ]
                if len(links) != len(raw_links):
                    raise SiteImportValidationError("SITE_IMPORT_INVALID")
                planned.append((category, links))
        except ValidationError as error:
            raise SiteImportValidationError("SITE_IMPORT_INVALID") from error

        current_categories = 0
        current_links = 0
        if mode == "merge":
            current_categories = (
                await self.session.scalar(
                    select(func.count())
                    .select_from(Category)
                    .where(Category.site_id == self.site.id)
                )
                or 0
            )
            current_links = (
                await self.session.scalar(
                    select(func.count()).select_from(Link).where(Link.site_id == self.site.id)
                )
                or 0
            )
        importing_links = sum(len(links) for _, links in planned)
        if current_categories + len(planned) > self.settings.max_categories_per_site:
            raise SiteLimitError(
                "CATEGORY_LIMIT_REACHED",
                current=current_categories,
                importing=len(planned),
                limit=self.settings.max_categories_per_site,
            )
        if current_links + importing_links > self.settings.max_links_per_site:
            raise SiteLimitError(
                "LINK_LIMIT_REACHED",
                current=current_links,
                importing=importing_links,
                limit=self.settings.max_links_per_site,
            )

        if mode == "replace":
            await self.session.execute(delete(Category).where(Category.site_id == self.site.id))
            await self.session.flush()
        last_category_order_value = await self.session.scalar(
            select(func.max(Category.sort_order)).where(Category.site_id == self.site.id)
        )
        last_category_order = (
            last_category_order_value if last_category_order_value is not None else -1
        )
        for category_offset, (category_data, links) in enumerate(planned, start=1):
            category = Category(
                site_id=self.site.id,
                sort_order=last_category_order + category_offset,
                **category_data.model_dump(),
            )
            self.session.add(category)
            await self.session.flush()
            self.session.add_all(
                [
                    Link(
                        site_id=self.site.id,
                        category_id=category.id,
                        sort_order=link_order,
                        **link_data.model_dump(exclude={"category_id"}),
                    )
                    for link_order, link_data in enumerate(links)
                ]
            )
        await self.session.commit()

    async def plan_bookmark_import(
        self,
        categories: list[BookmarkCategory],
        *,
        mode: Literal["replace", "merge"],
        duplicate_strategy: Literal["skip", "keep"],
        source_categories: int,
        source_links: int,
        unsupported_links: int,
    ) -> BookmarkImportPlan:
        existing_categories: dict[str, Category] = {}
        seen_urls: set[str] = set()
        current_categories = 0
        current_links = 0
        if mode == "merge":
            existing = list(
                (
                    await self.session.scalars(
                        select(Category).where(Category.site_id == self.site.id)
                    )
                ).all()
            )
            existing_categories = {
                category.name.strip().casefold(): category for category in existing
            }
            current_categories = len(existing)
            current_links = (
                await self.session.scalar(
                    select(func.count()).select_from(Link).where(Link.site_id == self.site.id)
                )
                or 0
            )
            if duplicate_strategy == "skip":
                urls = await self.session.scalars(
                    select(Link.url).where(Link.site_id == self.site.id)
                )
                seen_urls = {normalize_bookmark_url(url) for url in urls}

        planned: dict[str, PlannedBookmarkCategory] = {}
        duplicate_links = 0
        for source_category in categories:
            key = source_category.name.strip().casefold()
            existing = existing_categories.get(key)
            category = planned.setdefault(
                key,
                PlannedBookmarkCategory(
                    name=source_category.name,
                    existing_id=existing.id if existing else None,
                ),
            )
            category.source_links += len(source_category.links)
            for link in source_category.links:
                normalized = normalize_bookmark_url(link.url)
                if duplicate_strategy == "skip" and normalized in seen_urls:
                    duplicate_links += 1
                    continue
                seen_urls.add(normalized)
                category.links.append(link)

        return BookmarkImportPlan(
            mode=mode,
            duplicate_strategy=duplicate_strategy,
            source_categories=source_categories,
            source_links=source_links,
            accepted_links=sum(len(category.links) for category in categories),
            unsupported_links=unsupported_links,
            duplicate_links=duplicate_links,
            categories=[category for category in planned.values() if category.links],
            current_categories=current_categories,
            current_links=current_links,
            max_categories=self.settings.max_categories_per_site,
            max_links=self.settings.max_links_per_site,
        )

    async def _category(self, category_id: str) -> Category:
        category = await self.session.scalar(
            select(Category).where(Category.id == category_id, Category.site_id == self.site.id)
        )
        if category is None:
            raise ResourceNotFoundError("CATEGORY_NOT_FOUND")
        return category

    async def _link(self, link_id: str) -> Link:
        link = await self.session.scalar(
            select(Link).where(Link.id == link_id, Link.site_id == self.site.id)
        )
        if link is None:
            raise ResourceNotFoundError("LINK_NOT_FOUND")
        return link


def category_payload(category: Category) -> dict[str, Any]:
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "icon": category.icon,
        "sort_order": category.sort_order,
        "is_visible": category.is_visible,
    }


def link_payload(link: Link) -> dict[str, Any]:
    return {
        "id": link.id,
        "category_id": link.category_id,
        "name": link.name,
        "url": link.url,
        "description": link.description,
        "icon": link.icon,
        "tags": link.tags,
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
