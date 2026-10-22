"""Real Psycopg/SQLAlchemy queries through a disposable PostgreSQL protocol adapter.

Requires npm ci in database/tests and MCQ_RUN_DB_TESTS=1. This is not native
PostgreSQL authentication or multi-process concurrency validation.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.database import Database
from backend.app.main import create_app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("MCQ_RUN_DB_TESTS") != "1",
        reason="Set MCQ_RUN_DB_TESTS=1 for disposable PostgreSQL adapter tests",
    ),
]


@pytest.mark.parametrize(
    "mode,check,expected",
    [
        ("ready", "schema", "ok"),
        ("core", "pgvector", "missing"),
        ("empty", "schema", "missing"),
        ("mismatch", "schema", "migration_mismatch"),
        ("unprivileged", "runtime_role", "missing_readiness_permissions"),
        ("unsafe", "runtime_role", "unsafe_privileges"),
    ],
)
def test_real_driver_readiness_modes(settings, postgres_fixture, mode, check, expected):
    port = postgres_fixture(mode)
    config = settings.model_copy(
        update={
            "database_port": port,
            "database_name": "postgres",
            "database_user": "postgres",
            "database_pool_size": 1,
        }
    )
    app = create_app(config)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/v1/health/live").status_code == 200
        response = client.get("/api/v1/health/ready")
        assert response.json()["checks"][check] == expected, response.text
        assert response.status_code == (200 if mode == "ready" else 503), response.text


def test_real_transaction_commit_and_rollback(settings, postgres_fixture):
    port = postgres_fixture()
    config = settings.model_copy(
        update={
            "database_port": port,
            "database_name": "postgres",
            "database_user": "postgres",
            "database_pool_size": 1,
        }
    )
    database = Database(config)
    try:
        with database.session() as session:
            session.execute(text("INSERT INTO mcq.phase3_transaction_fixture VALUES (1)"))
        with database.session() as session:
            assert (
                session.execute(
                    text("SELECT count(*) FROM mcq.phase3_transaction_fixture")
                ).scalar_one()
                == 0
            )
        with database.session() as session, session.begin():
            session.execute(text("INSERT INTO mcq.phase3_transaction_fixture VALUES (2)"))
        with pytest.raises(RuntimeError), database.session() as session, session.begin():
            session.execute(text("INSERT INTO mcq.phase3_transaction_fixture VALUES (3)"))
            raise RuntimeError("fixture rollback")
        with database.session() as session:
            assert session.execute(
                text("SELECT id FROM mcq.phase3_transaction_fixture")
            ).scalars().all() == [2]
    finally:
        database.close()
