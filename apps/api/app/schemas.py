from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    icon: str = Field(default="🧭", max_length=8)
    template_id: str = "blank"
    theme: Literal["light", "dark", "system"] = "light"
    access_password: str | None = Field(default=None, min_length=6, max_length=128)
    captcha_token: str | None = Field(default=None, max_length=2048)
    captcha_answer: str | None = Field(default=None, max_length=16)


class SessionCreate(BaseModel):
    edit_key: str = Field(min_length=32, max_length=256)


class PasswordUnlock(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class LayoutConfig(BaseModel):
    accent_color: str = Field(default="#167D68", pattern=r"^#[0-9A-Fa-f]{6}$")
    canvas_style: Literal["clean", "soft", "contrast"] = "soft"
    card_style: Literal["solid", "outline", "minimal"] = "solid"
    content_width: Literal["compact", "standard", "wide"] = "standard"
    columns: Literal[2, 3, 4] = 3
    density: Literal["comfortable", "compact"] = "comfortable"
    header_alignment: Literal["left", "center"] = "left"
    wallpaper_url: str | None = Field(default=None, max_length=2048)
    wallpaper_fit: Literal["cover", "contain", "tile"] = "cover"
    wallpaper_position: Literal["top", "center", "bottom"] = "center"
    wallpaper_overlay: int = Field(default=40, ge=0, le=90)

    @field_validator("wallpaper_url")
    @classmethod
    def valid_wallpaper_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        parsed = urlparse(normalized)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("WALLPAPER_URL_INVALID")
        return normalized


class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=8)
    theme: Literal["light", "dark", "system"] | None = None
    allow_indexing: bool | None = None
    allow_public_bookmark_export: bool | None = None
    show_search: bool | None = None
    show_updated_at: bool | None = None
    show_visit_count: bool | None = None
    show_descriptions: bool | None = None
    show_tags: bool | None = None
    layout_config: LayoutConfig | None = None
    access_password: str | None = Field(default=None, max_length=128)

    @field_validator("access_password")
    @classmethod
    def valid_optional_password(cls, value: str | None) -> str | None:
        if value and len(value) < 6:
            raise ValueError("PASSWORD_TOO_SHORT")
        return value


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=300)
    icon: str = Field(default="📁", max_length=8)
    is_visible: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=8)
    is_visible: bool | None = None


class LinkCreate(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=3, max_length=2048)
    description: str | None = Field(default=None, max_length=300)
    icon: str = Field(default="🔗", max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=10)
    is_pinned: bool = False
    is_enabled: bool = True
    open_mode: Literal["new", "same"] = "new"

    @field_validator("url")
    @classmethod
    def allowed_url_scheme(cls, value: str) -> str:
        from urllib.parse import urlparse

        if urlparse(value).scheme.lower() not in {"http", "https", "mailto", "tel"}:
            raise ValueError("URL_PROTOCOL_NOT_ALLOWED")
        return value


class LinkUpdate(BaseModel):
    category_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=3, max_length=2048)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=8)
    tags: list[str] | None = Field(default=None, max_length=10)
    is_pinned: bool | None = None
    is_enabled: bool | None = None
    open_mode: Literal["new", "same"] | None = None

    @field_validator("url")
    @classmethod
    def allowed_url_scheme(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from urllib.parse import urlparse

        if urlparse(value).scheme.lower() not in {"http", "https", "mailto", "tel"}:
            raise ValueError("URL_PROTOCOL_NOT_ALLOWED")
        return value


class ReorderItem(BaseModel):
    id: str
    sort_order: int = Field(ge=0)


class LinkOrganizeItem(ReorderItem):
    category_id: str


class BatchLinks(BaseModel):
    lines: str = Field(min_length=1, max_length=100_000)
    category_id: str


class ImportRequest(BaseModel):
    mode: Literal["replace", "merge"]
    data: dict


class DeleteSite(BaseModel):
    confirm_name: str


class ReportCreate(BaseModel):
    reason: Literal["spam", "phishing", "illegal", "other"]
    description: str | None = Field(default=None, max_length=500)


class AdminSessionCreate(BaseModel):
    token: str = Field(min_length=16, max_length=512)


class AdminSiteUpdate(BaseModel):
    is_disabled: bool


class ReportUpdate(BaseModel):
    status: Literal["open", "resolved", "dismissed"]


class BookmarkImport(BaseModel):
    mode: Literal["replace", "merge"] = "merge"
    html: str = Field(min_length=1, max_length=5_000_000)


class CloneSite(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)


class AccountCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
