from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    generate_token,
    hash_password,
    token_digest,
    verify_password,
    verify_token,
)
from app.models import User, UserSession


class AccountAuthenticationError(Exception):
    pass


class AccountConflictError(Exception):
    pass


class AccountAuthorizationError(Exception):
    pass


class AccountAuth:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def register(self, email: str, password: str) -> tuple[User, str, str]:
        normalized = email.strip().lower()
        if await self.session.scalar(select(User).where(User.email == normalized)):
            raise AccountConflictError
        user = User(email=normalized, password_hash=hash_password(password))
        self.session.add(user)
        await self.session.flush()
        token, csrf = await self._create_session(user.id)
        await self.session.commit()
        return user, token, csrf

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = await self.session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not verify_password(password, user.password_hash):
            raise AccountAuthenticationError
        token, csrf = await self._create_session(user.id)
        await self.session.commit()
        return user, token, csrf

    async def authenticate(self, token: str | None) -> tuple[User, UserSession]:
        if not token:
            raise AccountAuthenticationError
        user_session = await self.session.scalar(
            select(UserSession).where(
                UserSession.token_hash == token_digest(token, self.settings.secret_key),
                UserSession.expires_at > datetime.now(UTC),
            )
        )
        if user_session is None:
            raise AccountAuthenticationError
        user = await self.session.get(User, user_session.user_id)
        if user is None:
            raise AccountAuthenticationError
        return user, user_session

    async def authenticate_optional(self, token: str | None) -> User | None:
        try:
            user, _ = await self.authenticate(token)
            return user
        except AccountAuthenticationError:
            return None

    async def restore(self, token: str | None) -> tuple[User, str]:
        if not token:
            raise AccountAuthenticationError
        user, user_session = await self.authenticate(token)
        csrf = self._csrf_token(token)
        user_session.csrf_token_hash = token_digest(csrf, self.settings.secret_key)
        user_session.expires_at = datetime.now(UTC) + timedelta(
            days=self.settings.account_session_days
        )
        await self.session.commit()
        return user, csrf

    def check_csrf(self, user_session: UserSession, token: str | None) -> None:
        if not token or not verify_token(
            token, user_session.csrf_token_hash, self.settings.secret_key
        ):
            raise AccountAuthorizationError

    async def logout(self, token: str | None) -> None:
        if token:
            await self.session.execute(
                delete(UserSession).where(
                    UserSession.token_hash == token_digest(token, self.settings.secret_key)
                )
            )
            await self.session.commit()

    async def _create_session(self, user_id: str) -> tuple[str, str]:
        await self.session.execute(
            delete(UserSession).where(UserSession.expires_at <= datetime.now(UTC))
        )
        token = generate_token()
        csrf = self._csrf_token(token)
        self.session.add(
            UserSession(
                user_id=user_id,
                token_hash=token_digest(token, self.settings.secret_key),
                csrf_token_hash=token_digest(csrf, self.settings.secret_key),
                expires_at=datetime.now(UTC) + timedelta(days=self.settings.account_session_days),
            )
        )
        return token, csrf

    def _csrf_token(self, session_token: str) -> str:
        return token_digest(f"account-csrf:{session_token}", self.settings.secret_key)
