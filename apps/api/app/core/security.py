import base64
import hashlib
import hmac
import secrets

import bcrypt


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def generate_slug() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(9)).decode().rstrip("=")


def token_digest(token: str, secret_key: str) -> str:
    return hmac.new(secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_token(token: str, digest: str, secret_key: str) -> bool:
    return hmac.compare_digest(token_digest(token, secret_key), digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, digest: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), digest.encode())
    except ValueError:
        return False
