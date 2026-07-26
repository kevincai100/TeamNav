from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    icon: str = Field(default="🧭", max_length=8)
    template_id: str = "blank"
    theme: Literal["light", "dark", "system"] = "light"
    access_password: str | None = Field(default=None, min_length=6, max_length=128)


class SessionCreate(BaseModel):
    edit_key: str = Field(min_length=32, max_length=256)


class PasswordUnlock(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=8)
    theme: Literal["light", "dark", "system"] | None = None
    allow_indexing: bool | None = None
    show_search: bool | None = None
    show_updated_at: bool | None = None
    show_visit_count: bool | None = None
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
