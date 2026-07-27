import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import Settings
from app.core.security import generate_token


class AdminAuthenticationError(Exception):
    pass


class AdminAuthorizationError(Exception):
    pass


class AdminAuth:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def exchange(self, supplied_token: str) -> tuple[str, str]:
        if not self.settings.admin_token or not hmac.compare_digest(
            supplied_token, self.settings.admin_token
        ):
            raise AdminAuthenticationError
        csrf = generate_token()
        payload = {
            "expires": int(time.time()) + self.settings.admin_session_hours * 3600,
            "csrf": self._digest(f"csrf:{csrf}"),
        }
        encoded = (
            base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )
        return f"{encoded}.{self._digest(f'session:{encoded}')}", csrf

    def authenticate(self, cookie: str | None) -> dict[str, Any]:
        if not cookie:
            raise AdminAuthenticationError
        try:
            encoded, signature = cookie.split(".", 1)
            if not hmac.compare_digest(signature, self._digest(f"session:{encoded}")):
                raise ValueError
            payload = json.loads(
                base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
            )
            if int(payload["expires"]) < int(time.time()):
                raise ValueError
            return payload
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise AdminAuthenticationError from error

    def check_csrf(self, payload: dict[str, Any], token: str | None) -> None:
        if not token or not hmac.compare_digest(
            str(payload["csrf"]), self._digest(f"csrf:{token}")
        ):
            raise AdminAuthorizationError

    def _digest(self, value: str) -> str:
        return hmac.new(
            self.settings.secret_key.encode(), value.encode(), hashlib.sha256
        ).hexdigest()
