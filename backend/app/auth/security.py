import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore
from uuid import UUID

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from ..config import Settings

ISSUER = "adaptive-mcq.local"
AUDIENCE = "adaptive-mcq-api"


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: int | None = None):
        self.status, self.code, self.message, self.retry_after = status, code, message, retry_after


def unauthorized():
    return AuthError(
        401, "INVALID_CREDENTIALS", "Credentials are invalid or the session has ended."
    )


class Security:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
        self.hash_slots = BoundedSemaphore(2)
        self.dummy_hash = self.hash_password(secrets.token_urlsafe(32))

    def hash_password(self, password: str) -> str:
        with self.hash_slots:
            return self.hasher.hash(password)

    def verify_password(self, stored_hash: str | None, password: str) -> bool:
        value = (
            stored_hash if stored_hash and stored_hash.startswith("$argon2id$") else self.dummy_hash
        )
        try:
            with self.hash_slots:
                passed = self.hasher.verify(value, password)
            return bool(stored_hash) and value != self.dummy_hash and passed
        except (VerificationError, InvalidHashError):
            return False

    def issue(self, user_id: UUID, session_id: UUID, issued_at: datetime) -> tuple[str, datetime]:
        expires = issued_at + timedelta(minutes=self.settings.access_token_minutes)
        payload = {
            "sub": str(user_id),
            "jti": str(session_id),
            "iat": int(issued_at.timestamp()),
            "nbf": int(issued_at.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "token_type": "access",
        }
        return jwt.encode(
            payload, self.settings.jwt_secret.get_secret_value(), algorithm="HS256"
        ), expires

    def decode(self, token: str) -> dict:
        if len(token) > 4096:
            raise unauthorized()
        try:
            claims = jwt.decode(
                token,
                self.settings.jwt_secret.get_secret_value(),
                algorithms=["HS256"],
                issuer=ISSUER,
                audience=AUDIENCE,
                options={
                    "require": ["sub", "jti", "iat", "nbf", "exp", "iss", "aud", "token_type"]
                },
            )
            if claims["token_type"] != "access":
                raise ValueError("wrong token type")
            for field in ("iat", "nbf", "exp"):
                if type(claims[field]) is not int:
                    raise ValueError("wrong timestamp type")
            if claims["exp"] <= claims["iat"]:
                raise ValueError("invalid expiry")
            claims["sub"], claims["jti"] = UUID(claims["sub"]), UUID(claims["jti"])
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
            raise unauthorized() from None

    def bucket_key(self, kind: str, value: str) -> str:
        return hmac.new(
            self.settings.jwt_secret.get_secret_value().encode(),
            f"auth-rate:{kind}:{value}".encode(),
            hashlib.sha256,
        ).hexdigest()


def utc_now():
    return datetime.now(timezone.utc)
