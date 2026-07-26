from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import generate_token, token_digest, verify_password, verify_token
from app.models import AccessSession, ManageSession, Site


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class ManageAuth:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def exchange_key(self, site: Site, edit_key: str) -> tuple[str, str]:
        if not verify_token(edit_key, site.edit_key_hash, self.settings.secret_key):
            raise AuthenticationError
        session_token = generate_token()
        csrf_token = generate_token()
        self.session.add(
            ManageSession(
                site_id=site.id,
                token_hash=token_digest(session_token, self.settings.secret_key),
                csrf_token_hash=token_digest(csrf_token, self.settings.secret_key),
                expires_at=datetime.now(UTC) + timedelta(days=self.settings.edit_session_days),
            )
        )
        await self.session.commit()
        return session_token, csrf_token

    async def authenticate(
        self, slug: str, session_token: str | None
    ) -> tuple[Site, ManageSession]:
        if not session_token:
            raise AuthenticationError
        digest = token_digest(session_token, self.settings.secret_key)
        result = await self.session.execute(
            select(ManageSession)
            .join(Site)
            .where(
                ManageSession.token_hash == digest,
                ManageSession.expires_at > datetime.now(UTC),
                Site.public_slug == slug,
                Site.deleted_at.is_(None),
                Site.is_disabled.is_(False),
            )
        )
        manage_session = result.scalar_one_or_none()
        if manage_session is None:
            raise AuthenticationError
        site = await self.session.get(Site, manage_session.site_id)
        if site is None:
            raise AuthenticationError
        return site, manage_session

    def check_csrf(self, manage_session: ManageSession, csrf_token: str | None) -> None:
        if not csrf_token or not verify_token(
            csrf_token, manage_session.csrf_token_hash, self.settings.secret_key
        ):
            raise AuthorizationError

    async def revoke_all(self, site_id: str) -> None:
        await self.session.execute(delete(ManageSession).where(ManageSession.site_id == site_id))


class AccessAuth:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def unlock(self, site: Site, password: str) -> str:
        if not site.access_password_hash or not verify_password(
            password, site.access_password_hash
        ):
            raise AuthenticationError
        token = generate_token()
        self.session.add(
            AccessSession(
                site_id=site.id,
                token_hash=token_digest(token, self.settings.secret_key),
                password_version=site.password_version,
                expires_at=datetime.now(UTC)
                + timedelta(hours=self.settings.access_session_hours),
            )
        )
        await self.session.commit()
        return token

    async def is_authorized(self, site: Site, token: str | None) -> bool:
        if not site.access_password_hash:
            return True
        if not token:
            return False
        session = await self.session.scalar(
            select(AccessSession).where(
                AccessSession.site_id == site.id,
                AccessSession.token_hash == token_digest(token, self.settings.secret_key),
                AccessSession.password_version == site.password_version,
                AccessSession.expires_at > datetime.now(UTC),
            )
        )
        return session is not None
