from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from backend.app.auth.schemas import RegisterRequest
from backend.app.auth.security import AUDIENCE, ISSUER, AuthError, Security, utc_now


@pytest.fixture
def security(settings):
    return Security(settings)


def test_argon2_hash_is_salted_and_verifies(security):
    password = "fixture password 123!"
    first, second = security.hash_password(password), security.hash_password(password)
    assert first != second
    assert first.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert password not in first
    assert security.verify_password(first, password)
    assert not security.verify_password(first, "incorrect")
    assert not security.verify_password(None, password)
    assert not security.verify_password("invalid-legacy-value", password)


def test_token_round_trip_has_no_role_or_password_claim(security):
    uid, sid = uuid4(), uuid4()
    token, _ = security.issue(uid, sid, utc_now())
    claims = security.decode(token)
    assert claims["sub"] == uid and claims["jti"] == sid
    assert "roles" not in claims and "password" not in claims
    assert claims["exp"] - claims["iat"] == 900


@pytest.mark.parametrize(
    "change",
    [
        "expired",
        "future",
        "wrong_issuer",
        "wrong_audience",
        "wrong_type",
        "missing_jti",
        "bad_subject",
        "string_time",
        "wrong_key",
        "wrong_algorithm",
        "unsigned",
    ],
)
def test_invalid_tokens_are_rejected(security, settings, change):
    now = int(utc_now().timestamp())
    claims = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + 900,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "token_type": "access",
    }
    key, algorithm = settings.jwt_secret.get_secret_value(), "HS256"
    if change == "expired":
        claims.update(iat=now - 1800, nbf=now - 1800, exp=now - 1)
    elif change == "future":
        claims.update(iat=now + 3600, nbf=now + 3600, exp=now + 4500)
    elif change == "wrong_issuer":
        claims["iss"] = "other"
    elif change == "wrong_audience":
        claims["aud"] = "other"
    elif change == "wrong_type":
        claims["token_type"] = "refresh"
    elif change == "missing_jti":
        del claims["jti"]
    elif change == "bad_subject":
        claims["sub"] = "not-a-uuid"
    elif change == "string_time":
        claims["iat"] = str(now)
    elif change == "wrong_key":
        key = "different-fixture-secret-12345678901234567890123456789012345678901234567890"
    elif change == "wrong_algorithm":
        algorithm = "HS512"
        key = key + key
    elif change == "unsigned":
        key, algorithm = "", "none"
    token = jwt.encode(claims, key, algorithm=algorithm)
    with pytest.raises(AuthError) as exc:
        security.decode(token)
    assert exc.value.status == 401


def test_garbage_and_oversized_tokens(security):
    for value in ("garbage", "a" * 5000):
        with pytest.raises(AuthError):
            security.decode(value)


def test_registration_cannot_accept_role_or_unknown_fields():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="student@example.com",
            display_name="Student",
            password="long-fixture-password",
            role="teacher",
        )


def test_registration_normalizes_email_not_password():
    payload = RegisterRequest(
        email="Student@Example.com", display_name=" Student ", password="  long-fixture-password  "
    )
    assert payload.email == "student@example.com"
    assert payload.display_name == "Student"
    assert payload.password.get_secret_value() == "  long-fixture-password  "


def test_rate_identifiers_are_domain_separated_and_private(security):
    assert security.bucket_key("login-ip", "127.0.0.1") != security.bucket_key(
        "register-ip", "127.0.0.1"
    )
    assert len(security.bucket_key("account", "person@example.com")) == 64
