from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


@dataclass
class BookmarkLink:
    name: str
    url: str
    tags: list[str] = field(default_factory=list)


@dataclass
class BookmarkCategory:
    name: str
    links: list[BookmarkLink] = field(default_factory=list)


@dataclass
class BookmarkInspection:
    categories: list[BookmarkCategory]
    source_categories: int
    source_links: int
    unsupported_links: int


def _is_supported_url(value: str) -> bool:
    if not value or any(character.isspace() for character in value):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    scheme = parsed.scheme.lower()
    if scheme in {"mailto", "tel"}:
        return bool(parsed.path)
    try:
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    return scheme in {"http", "https"} and bool(hostname)


class _NetscapeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.categories: list[BookmarkCategory] = []
        self.folder_stack: list[tuple[str, BookmarkCategory] | None] = []
        self.pending_folder: tuple[str, BookmarkCategory] | None = None
        self.root_category: BookmarkCategory | None = None
        self.source_categories = 0
        self.source_links = 0
        self.unsupported_links = 0
        self.capture: str | None = None
        self.buffer: list[str] = []
        self.link_attrs: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "dl":
            self.folder_stack.append(self.pending_folder)
            self.pending_folder = None
            return
        if lowered in {"h3", "a"}:
            self.capture = lowered
            self.buffer = []
            self.link_attrs = {key.lower(): value or "" for key, value in attrs}

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "dl":
            if self.folder_stack:
                self.folder_stack.pop()
            return
        if lowered != self.capture:
            return
        name = "".join(self.buffer).strip()
        if lowered == "h3" and name:
            self.source_categories += 1
            folder_name = name[:50]
            path = [folder[0] for folder in self.folder_stack if folder]
            category = BookmarkCategory(name=_category_path([*path, folder_name]))
            self.categories.append(category)
            self.pending_folder = (folder_name, category)
        elif lowered == "a":
            self.source_links += 1
            url = self.link_attrs.get("href", "").strip()
            if name and _is_supported_url(url):
                current = (
                    self.folder_stack[-1][1]
                    if self.folder_stack and self.folder_stack[-1]
                    else None
                )
                if current is None:
                    if self.root_category is None:
                        self.root_category = BookmarkCategory(name="Imported bookmarks")
                        self.categories.append(self.root_category)
                    current = self.root_category
                tags = [item.strip()[:30] for item in self.link_attrs.get("tags", "").split(",")]
                current.links.append(
                    BookmarkLink(
                        name=name[:100], url=url[:2048], tags=[tag for tag in tags if tag][:10]
                    )
                )
            else:
                self.unsupported_links += 1
        self.capture = None
        self.buffer = []


def _category_path(parts: list[str]) -> str:
    path = " / ".join(parts)
    return path if len(path) <= 50 else f"...{path[-47:]}"


class BookmarkCodec:
    @staticmethod
    def parse(value: str) -> list[BookmarkCategory]:
        return BookmarkCodec.inspect(value).categories

    @staticmethod
    def inspect(value: str) -> BookmarkInspection:
        parser = _NetscapeParser()
        parser.feed(value)
        return BookmarkInspection(
            categories=[category for category in parser.categories if category.links],
            source_categories=parser.source_categories,
            source_links=parser.source_links,
            unsupported_links=parser.unsupported_links,
        )

    @staticmethod
    def export(site_name: str, categories: list, *, public: bool = False) -> str:
        lines = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            f"<TITLE>{escape(site_name)}</TITLE>",
            f"<H1>{escape(site_name)}</H1>",
            "<DL><p>",
        ]
        for category in categories:
            if public and not category.is_visible:
                continue
            links = [link for link in category.links if not public or link.is_enabled]
            if public and not links:
                continue
            lines.extend([f"  <DT><H3>{escape(category.name)}</H3>", "  <DL><p>"])
            for link in links:
                tags = escape(",".join(link.tags), quote=True)
                href = escape(link.url, quote=True)
                name = escape(link.name)
                lines.append(
                    f'    <DT><A HREF="{href}" TAGS="{tags}">{name}</A>'
                )
            lines.append("  </DL><p>")
        lines.append("</DL><p>")
        return "\n".join(lines)
