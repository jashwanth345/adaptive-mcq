"""Local operator-only account provisioning. No passwords accepted in command arguments."""

import argparse
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .app.auth.schemas import RegisterRequest
from .app.auth.security import Security
from .app.auth.service import audit
from .app.config import ConfigurationError, load_settings
from .app.database import Database


def assert_operator(session):
    allowed = session.execute(
        text(
            "SELECT pg_has_role(current_user,nspowner,'MEMBER') FROM pg_namespace WHERE nspname='mcq'"
        )
    ).scalar_one_or_none()
    if not allowed:
        raise ConfigurationError(
            "The local operator command requires the trusted schema-owner login."
        )


def provision_teacher(database, security, payload):
    with database.session() as session, session.begin():
        assert_operator(session)
        uid = session.execute(
            text(
                "INSERT INTO mcq.users(email,display_name,password_hash) VALUES(:email,:name,:hash) RETURNING id"
            ),
            {
                "email": payload.email,
                "name": payload.display_name,
                "hash": security.hash_password(payload.password.get_secret_value()),
            },
        ).scalar_one()
        session.execute(
            text("INSERT INTO mcq.user_roles(user_id,role) VALUES(:id,'teacher')"), {"id": uid}
        )
        audit(session, "operator.teacher_created", uid)
        return uid


def manage_user(database, email: str, command: str):
    with database.session() as session, session.begin():
        assert_operator(session)
        uid = session.execute(
            text("SELECT id FROM mcq.users WHERE email=:email FOR UPDATE"), {"email": email}
        ).scalar_one_or_none()
        if uid is None:
            raise ConfigurationError("The requested account was not found.")
        if command == "grant-teacher":
            session.execute(
                text(
                    "INSERT INTO mcq.user_roles(user_id,role) VALUES(:id,'teacher') ON CONFLICT DO NOTHING"
                ),
                {"id": uid},
            )
        elif command == "revoke-teacher":
            session.execute(
                text("DELETE FROM mcq.user_roles WHERE user_id=:id AND role='teacher'"), {"id": uid}
            )
        elif command in ("disable-user", "enable-user"):
            session.execute(
                text("UPDATE mcq.users SET active=:active WHERE id=:id"),
                {"id": uid, "active": command == "enable-user"},
            )
        else:
            raise ConfigurationError("Unknown operator operation.")
        session.execute(
            text(
                "UPDATE mcq.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=:id AND revoked_at IS NULL"
            ),
            {"id": uid},
        )
        audit(session, "operator." + command.replace("-", "_"), uid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "create-teacher",
            "grant-teacher",
            "revoke-teacher",
            "disable-user",
            "enable-user",
        ],
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", help="Display name, required for create-teacher")
    args = parser.parse_args()
    database = None
    try:
        email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
        settings = load_settings()
        database = Database(settings)
        if args.command == "create-teacher":
            if not args.name:
                parser.error("create-teacher requires --name")
            password = getpass.getpass("New teacher password (12–128 characters): ")
            if password != getpass.getpass("Confirm password: "):
                raise ConfigurationError("Passwords did not match.")
            payload = RegisterRequest(email=email, display_name=args.name, password=password)
            provision_teacher(database, Security(settings), payload)
        else:
            manage_user(database, email, args.command)
        print("Account operation committed. No token was issued; sign in through the API.")
        return 0
    except (ConfigurationError, ValidationError):
        print(
            "Account operation not completed. Check local operator credentials and validated account details.",
            file=sys.stderr,
        )
        return 2
    except SQLAlchemyError:
        print(
            "Account operation not completed. Check schema, permissions and duplicate account details.",
            file=sys.stderr,
        )
        return 1
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    raise SystemExit(main())
