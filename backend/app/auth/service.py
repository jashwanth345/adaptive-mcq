import math
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..config import Settings
from ..database import Database
from .schemas import RegisterRequest
from .security import AuthError, Security, unauthorized, utc_now


@dataclass(frozen=True)
class Principal:
    user: dict
    session_id: UUID


def public_user(session, row) -> dict:
    roles = (
        session.execute(
            text("SELECT role FROM mcq.user_roles WHERE user_id=:id ORDER BY role"),
            {"id": row["id"]},
        )
        .scalars()
        .all()
    )
    return {key: row[key] for key in ("id", "email", "display_name", "created_at")} | {
        "roles": roles
    }


def audit(session, event: str, user_id: UUID | None):
    if event.startswith("operator."):
        session.execute(
            text("""INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id,details)
            VALUES(NULL,:event,'user',:id,jsonb_build_object('database_actor',current_user))"""),
            {"id": user_id, "event": event},
        )
        return
    session.execute(
        text(
            "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:id,:event,'user',:id)"
        ),
        {"id": user_id, "event": event},
    )


class AuthService:
    def __init__(self, database: Database, settings: Settings):
        self.database, self.settings = database, settings
        self.security = Security(settings)

    def ensure_ready(self):
        if self.database.readiness()["status"] != "ready":
            raise AuthError(503, "AUTH_UNAVAILABLE", "Local authentication storage is not ready.")

    def consume_rate(self, kind: str, value: str, limit: int):
        key = self.security.bucket_key(kind, value)
        with self.database.session() as session, session.begin():
            row = (
                session.execute(
                    text("""
                INSERT INTO mcq.auth_rate_limits(bucket_key,attempts,expires_at)
                VALUES(:key,1,clock_timestamp()+make_interval(secs => :seconds))
                ON CONFLICT(bucket_key) DO UPDATE SET
                    attempts = CASE WHEN auth_rate_limits.expires_at <= clock_timestamp() THEN 1
                               ELSE least(auth_rate_limits.attempts+1,1000000) END,
                    expires_at = CASE WHEN auth_rate_limits.expires_at <= clock_timestamp()
                                 THEN clock_timestamp()+make_interval(secs => :seconds)
                                 ELSE auth_rate_limits.expires_at END
                RETURNING attempts, greatest(1,ceil(extract(epoch FROM expires_at-clock_timestamp()))) AS retry
            """),
                    {"key": key, "seconds": self.settings.auth_window_seconds},
                )
                .mappings()
                .one()
            )
        # Raising inside the transaction would roll back the attempt counter.
        if row["attempts"] > limit:
            raise AuthError(
                429, "RATE_LIMITED", "Too many attempts. Try again later.", math.ceil(row["retry"])
            )

    def register(self, payload: RegisterRequest, peer: str, *, teacher=False):
        self.ensure_ready()
        self.consume_rate("register-ip", peer, self.settings.auth_register_ip_limit)
        hashed = self.security.hash_password(payload.password.get_secret_value())
        try:
            with self.database.session() as session, session.begin():
                uid = session.execute(
                    text("SELECT mcq.register_teacher(:email,:name,:hash)" if teacher
                         else "SELECT mcq.register_student(:email,:name,:hash)"),
                    {"email": payload.email, "name": payload.display_name, "hash": hashed},
                ).scalar_one()
                if uid is None:
                    raise AuthError(
                        409,
                        "ACCOUNT_UNAVAILABLE",
                        "An account cannot be created with these details.",
                    )
                row = (
                    session.execute(
                        text("SELECT id,email,display_name,created_at FROM mcq.users WHERE id=:id"),
                        {"id": uid},
                    )
                    .mappings()
                    .one()
                )
                return public_user(session, row)
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise AuthError(
                    409, "ACCOUNT_UNAVAILABLE", "An account cannot be created with these details."
                ) from None
            raise

    def login(self, email: str, password: str, peer: str):
        self.ensure_ready()
        self.consume_rate("login-ip", peer, self.settings.auth_login_ip_limit)
        self.consume_rate("login-account", email, self.settings.auth_login_account_limit)
        result = None
        with self.database.session() as session, session.begin():
            row = (
                session.execute(
                    text("SELECT * FROM mcq.users WHERE email=:email FOR UPDATE"), {"email": email}
                )
                .mappings()
                .one_or_none()
            )
            valid = self.security.verify_password(row["password_hash"] if row else None, password)
            if row and row["active"] and valid:
                user = public_user(session, row)
                if user["roles"]:
                    if self.security.hasher.check_needs_rehash(row["password_hash"]):
                        session.execute(
                            text("UPDATE mcq.users SET password_hash=:hash WHERE id=:id"),
                            {"id": row["id"], "hash": self.security.hash_password(password)},
                        )
                    sid, now = uuid4(), utc_now()
                    token, expires = self.security.issue(row["id"], sid, now)
                    session.execute(
                        text(
                            "INSERT INTO mcq.auth_sessions(id,user_id,created_at,expires_at) VALUES(:sid,:uid,:created,:expires)"
                        ),
                        {"sid": sid, "uid": row["id"], "created": now, "expires": expires},
                    )
                    audit(session, "auth.login", row["id"])
                    result = {
                        "access_token": token,
                        "token_type": "bearer",
                        "expires_in": self.settings.access_token_minutes * 60,
                        "user": user,
                    }
            if result is None:
                audit(session, "auth.login_failed", row["id"] if row else None)
        if result is None:
            raise unauthorized()
        return result

    def authenticate(self, token: str) -> Principal:
        claims = self.security.decode(token)
        self.ensure_ready()
        with self.database.session() as session:
            row = (
                session.execute(
                    text("""
                SELECT u.* FROM mcq.users u JOIN mcq.auth_sessions s ON s.user_id=u.id
                WHERE u.id=:uid AND s.id=:sid AND u.active AND s.revoked_at IS NULL
                  AND s.expires_at>clock_timestamp()
            """),
                    {"uid": claims["sub"], "sid": claims["jti"]},
                )
                .mappings()
                .one_or_none()
            )
            if not row:
                raise unauthorized()
            user = public_user(session, row)
            if not user["roles"]:
                raise unauthorized()
            return Principal(user, claims["jti"])

    def logout(self, principal: Principal, all_sessions: bool = False):
        with self.database.session() as session, session.begin():
            # Same user -> session lock order as login/password change/operator commands.
            session.execute(
                text("SELECT id FROM mcq.users WHERE id=:id FOR UPDATE"),
                {"id": principal.user["id"]},
            )
            predicate = "" if all_sessions else " AND id=:sid"
            session.execute(
                text(
                    "UPDATE mcq.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=:uid AND revoked_at IS NULL"
                    + predicate
                ),
                {"uid": principal.user["id"], "sid": principal.session_id},
            )
            audit(
                session, "auth.logout_all" if all_sessions else "auth.logout", principal.user["id"]
            )

    def change_password(self, principal: Principal, current_password: str, new_password: str):
        uid = principal.user["id"]
        self.consume_rate("password-change", str(uid), self.settings.auth_login_account_limit)
        with self.database.session() as session, session.begin():
            row = (
                session.execute(
                    text("SELECT password_hash,active FROM mcq.users WHERE id=:id FOR UPDATE"),
                    {"id": uid},
                )
                .mappings()
                .one()
            )
            still_valid = session.execute(
                text(
                    "SELECT 1 FROM mcq.auth_sessions WHERE id=:sid AND revoked_at IS NULL AND expires_at>clock_timestamp()"
                ),
                {"sid": principal.session_id},
            ).scalar_one_or_none()
            if (
                not row["active"]
                or not still_valid
                or not self.security.verify_password(row["password_hash"], current_password)
            ):
                raise unauthorized()
            if new_password == current_password:
                raise AuthError(400, "PASSWORD_UNCHANGED", "Choose a different password.")
            session.execute(
                text("UPDATE mcq.users SET password_hash=:hash WHERE id=:id"),
                {"id": uid, "hash": self.security.hash_password(new_password)},
            )
            session.execute(
                text(
                    "UPDATE mcq.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=:id AND revoked_at IS NULL"
                ),
                {"id": uid},
            )
            audit(session, "auth.password_changed", uid)
