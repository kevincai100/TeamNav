from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TeamNav"
    app_url: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./teamnav.db"
    secret_key: str = Field(default="development-only-change-this-secret-key", min_length=32)
    edit_session_days: int = Field(default=7, ge=1, le=365)
    access_session_hours: int = Field(default=24, ge=1, le=24 * 30)
    account_session_days: int = Field(default=30, ge=1, le=365)
    max_sites_per_ip_per_hour: int = Field(default=5, ge=1)
    max_sites_per_ip_per_day: int = Field(default=20, ge=1)
    max_categories_per_site: int = Field(default=200, ge=1)
    max_links_per_site: int = Field(default=2_000, ge=1)
    default_noindex: bool = True
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    admin_token: str = ""
    admin_session_hours: int = Field(default=8, ge=1, le=24 * 7)
    captcha_required: bool = True
    captcha_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    captcha_expose_test_answer: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("admin_token")
    @classmethod
    def validate_admin_token(cls, value: str) -> str:
        if value.startswith("replace-with-"):
            raise ValueError("ADMIN_TOKEN must not use the example placeholder")
        if value and len(value) < 32:
            raise ValueError("ADMIN_TOKEN must contain at least 32 characters")
        return value

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if value.startswith("replace-with-"):
            raise ValueError("SECRET_KEY must not use the example placeholder")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
