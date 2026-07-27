from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TeamNav"
    app_url: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./teamnav.db"
    secret_key: str = Field(default="development-only-change-this-secret-key")
    edit_session_days: int = 7
    access_session_hours: int = 24
    account_session_days: int = 30
    max_sites_per_ip_per_hour: int = 5
    max_sites_per_ip_per_day: int = 20
    max_categories_per_site: int = 30
    max_links_per_site: int = 500
    default_noindex: bool = True
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    admin_token: str = ""
    admin_session_hours: int = 8
    captcha_required: bool = True
    captcha_ttl_seconds: int = 300
    captcha_expose_test_answer: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
