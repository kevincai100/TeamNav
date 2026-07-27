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


class _NetscapeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.categories: list[BookmarkCategory] = []
        self.current: BookmarkCategory | None = None
        self.capture: str | None = None
        self.buffer: list[str] = []
        self.link_attrs: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"h3", "a"}:
            self.capture = lowered
            self.buffer = []
            self.link_attrs = {key.lower(): value or "" for key, value in attrs}

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered != self.capture:
            return
        name = "".join(self.buffer).strip()
        if lowered == "h3" and name:
            self.current = BookmarkCategory(name=name[:50])
            self.categories.append(self.current)
        elif lowered == "a" and name:
            url = self.link_attrs.get("href", "").strip()
            if urlparse(url).scheme.lower() in {"http", "https", "mailto", "tel"}:
                if self.current is None:
                    self.current = BookmarkCategory(name="Imported bookmarks")
                    self.categories.append(self.current)
                tags = [item.strip()[:30] for item in self.link_attrs.get("tags", "").split(",")]
                self.current.links.append(
                    BookmarkLink(
                        name=name[:100], url=url[:2048], tags=[tag for tag in tags if tag][:10]
                    )
                )
        self.capture = None
        self.buffer = []


class BookmarkCodec:
    @staticmethod
    def parse(value: str) -> list[BookmarkCategory]:
        parser = _NetscapeParser()
        parser.feed(value)
        return [category for category in parser.categories if category.links]

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
