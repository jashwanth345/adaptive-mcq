from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.orm import Session, sessionmaker

from database.migrate import inventory

from .config import Settings, validate_process_environment


def expected_history() -> dict[str, str]:
    return {name: checksum for name, checksum, _ in inventory()}


class Database:
    def __init__(self, settings: Settings):
        validate_process_environment()
        url = URL.create(
            "postgresql+psycopg",
            username=settings.database_user,
            password=settings.database_password.get_secret_value(),
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
        )
        self.engine = create_engine(
            url,
            pool_size=settings.database_pool_size,
            max_overflow=0,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_pre_ping=True,
            hide_parameters=True,
            echo=False,
            connect_args={
                "hostaddr": settings.database_host,
                "connect_timeout": settings.database_connect_timeout_seconds,
                "sslmode": "disable",
                "application_name": "adaptive_mcq_backend",
                "options": f"-c statement_timeout={settings.database_statement_timeout_ms} -c lock_timeout=1000 -c timezone=UTC -c search_path=mcq,public",
            },
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        self.manifest = expected_history()

    @contextmanager
    def session(self) -> Iterator[Session]:
        # Services must use session.begin() / commit explicitly; uncommitted work rolls back.
        with self.sessions() as session:
            try:
                yield session
            finally:
                session.rollback()

    def close(self):
        self.engine.dispose()

    def readiness(self) -> dict:
        checks = {
            "database": "unavailable",
            "schema": "not_checked",
            "pgvector": "not_checked",
            "runtime_role": "not_checked",
            "auth_permissions": "not_checked",
        }
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SELECT 1"))
                checks["database"] = "ok"
                extension = connection.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                ).scalar_one_or_none()
                checks["pgvector"] = "ok" if extension else "missing"
                ledger = connection.execute(
                    text("SELECT to_regclass('mcq_meta.schema_migrations')")
                ).scalar_one_or_none()
                if ledger is None:
                    checks["schema"] = "missing"
                else:
                    history = dict(
                        connection.execute(
                            text("SELECT version, checksum FROM mcq_meta.schema_migrations")
                        )
                        .tuples()
                        .all()
                    )
                    checks["schema"] = "ok" if history == self.manifest else "migration_mismatch"
                unsafe = connection.execute(
                    text("""
                    SELECT r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls
                      OR pg_has_role(current_user, d.datdba, 'MEMBER')
                      OR EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspname IN ('mcq','mcq_meta')
                                 AND pg_has_role(current_user, n.nspowner, 'MEMBER'))
                    FROM pg_roles r CROSS JOIN pg_database d
                    WHERE r.rolname = current_user AND d.datname = current_database()
                """)
                ).scalar_one()
                checks["runtime_role"] = "unsafe_privileges" if unsafe else "ok"
                if checks["schema"] == "ok":
                    allowed = connection.execute(
                        text("""
                        SELECT has_table_privilege(current_user,'mcq.users','SELECT')
                          AND has_table_privilege(current_user,'mcq.user_roles','SELECT')
                          AND has_column_privilege(current_user,'mcq.users','password_hash','UPDATE')
                          AND NOT has_column_privilege(current_user,'mcq.users','active','UPDATE')
                          AND NOT has_table_privilege(current_user,'mcq.users','INSERT,DELETE')
                          AND NOT has_table_privilege(current_user,'mcq.user_roles','INSERT,UPDATE,DELETE')
                          AND has_function_privilege(current_user,'mcq.register_student(text,text,text)','EXECUTE')
                          AND has_function_privilege(current_user,'mcq.register_teacher(text,text,text)','EXECUTE')
                          AND has_table_privilege(current_user,'mcq.auth_sessions','SELECT')
                          AND has_table_privilege(current_user,'mcq.auth_sessions','INSERT')
                          AND has_column_privilege(current_user,'mcq.auth_sessions','revoked_at','UPDATE')
                          AND NOT has_column_privilege(current_user,'mcq.auth_sessions','expires_at','UPDATE')
                          AND has_table_privilege(current_user,'mcq.auth_rate_limits','SELECT')
                          AND has_table_privilege(current_user,'mcq.auth_rate_limits','INSERT')
                          AND has_table_privilege(current_user,'mcq.auth_rate_limits','UPDATE')
                          AND has_table_privilege(current_user,'mcq.audit_events','INSERT')
                          AND has_sequence_privilege(current_user,'mcq.audit_events_id_seq','USAGE')
                    """)
                    ).scalar_one()
                    checks["auth_permissions"] = (
                        "ok" if allowed else "missing_or_excessive_auth_permissions"
                    )
        except PoolTimeout:
            checks["database"] = "busy"
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "42501":
                checks["runtime_role"] = "missing_readiness_permissions"
            elif code == "57014":
                checks["database"] = "timeout"
            else:
                checks["database"] = "unavailable"
        except SQLAlchemyError:
            checks["database"] = "unavailable"
        return {
            "status": "ready" if all(v == "ok" for v in checks.values()) else "not_ready",
            "scope": "backend_foundation",
            "checks": checks,
        }
