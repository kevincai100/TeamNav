import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import Settings


class CaptchaError(Exception):
    pass


class CaptchaVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def challenge(self) -> dict[str, Any]:
        left = secrets.randbelow(8) + 2
        right = secrets.randbelow(8) + 2
        nonce = secrets.token_urlsafe(12)
        expires = int(time.time()) + self.settings.captcha_ttl_seconds
        answer_digest = self._answer_digest(nonce, str(left + right))
        payload = {"nonce": nonce, "expires": expires, "answer": answer_digest}
        encoded = self._encode(payload)
        token = f"{encoded}.{self._signature(encoded)}"
        result: dict[str, Any] = {
            "required": self.settings.captcha_required,
            "prompt": f"{left} + {right} = ?",
            "token": token,
            "expires_in": self.settings.captcha_ttl_seconds,
        }
        if self.settings.captcha_expose_test_answer:
            result["test_answer"] = left + right
        return result

    def verify(self, token: str | None, answer: str | None) -> None:
        if not self.settings.captcha_required:
            return
        if not token or answer is None:
            raise CaptchaError("CAPTCHA_REQUIRED")
        try:
            encoded, signature = token.split(".", 1)
            if not hmac.compare_digest(signature, self._signature(encoded)):
                raise ValueError
            payload = json.loads(self._decode(encoded))
            if int(payload["expires"]) < int(time.time()):
                raise ValueError
            expected = self._answer_digest(str(payload["nonce"]), answer.strip())
            if not hmac.compare_digest(str(payload["answer"]), expected):
                raise ValueError
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CaptchaError("CAPTCHA_INVALID") from error

    def _signature(self, value: str) -> str:
        return hmac.new(
            self.settings.secret_key.encode(), f"captcha:{value}".encode(), hashlib.sha256
        ).hexdigest()

    def _answer_digest(self, nonce: str, answer: str) -> str:
        return hmac.new(
            self.settings.secret_key.encode(), f"answer:{nonce}:{answer}".encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _encode(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def _decode(value: str) -> str:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
