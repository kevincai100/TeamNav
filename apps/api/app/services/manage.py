from typing import Any, Literal

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
from app.services.bookmarks import BookmarkCategory


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
        created: list[Link] = []
        for raw_line in lines.splitlines():
            parts = [part.strip() for part in raw_line.split("|")]
            if len(parts) < 2 or not parts[0] or not parts[1]:
                continue
            created.append(
                await self.create_link(
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
            )
        return created

    async def import_bookmarks(
        self,
        categories: list[BookmarkCategory],
        mode: Literal["replace", "merge"],
    ) -> tuple[int, int]:
        importing_categories = len(categories)
        importing_links = sum(len(category.links) for category in categories)
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
        if current_categories + importing_categories > self.settings.max_categories_per_site:
            raise SiteLimitError(
                "BOOKMARK_IMPORT_CATEGORY_LIMIT_REACHED",
                current=current_categories,
                importing=importing_categories,
                limit=self.settings.max_categories_per_site,
            )
        if current_links + importing_links > self.settings.max_links_per_site:
            raise SiteLimitError(
                "BOOKMARK_IMPORT_LINK_LIMIT_REACHED",
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
        for category_offset, category_data in enumerate(categories, start=1):
            category = Category(
                site_id=self.site.id,
                name=category_data.name,
                sort_order=last_category_order + category_offset,
            )
            self.session.add(category)
            await self.session.flush()
            for link_order, link_data in enumerate(category_data.links):
                self.session.add(
                    Link(
                        site_id=self.site.id,
                        category_id=category.id,
                        name=link_data.name,
                        url=link_data.url,
                        tags=link_data.tags,
                        sort_order=link_order,
                    )
                )
        await self.session.commit()
        return importing_categories, importing_links

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
    }
