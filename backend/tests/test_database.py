from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError, TimeoutError

from backend.app.database import Database, expected_history


def test_engine_uses_small_pool_and_explicit_local_connection(settings):
    with patch("backend.app.database.create_engine") as factory:
        Database(settings)
    kwargs = factory.call_args.kwargs
    assert kwargs["pool_size"] == 2
    assert kwargs["max_overflow"] == 0
    assert kwargs["hide_parameters"] is True
    assert kwargs["connect_args"]["hostaddr"] == "127.0.0.1"
    assert "service" not in kwargs["connect_args"]
    assert "fixture-password" not in str(factory.call_args.args[0])


def test_session_never_implicitly_commits(settings):
    database = Database(settings)
    session = MagicMock()
    database.sessions = MagicMock(return_value=session)
    session.__enter__.return_value = session
    try:
        with database.session():
            pass
        session.commit.assert_not_called()
        session.rollback.assert_called_once()
    finally:
        database.close()


def test_session_rolls_back_on_exception(settings):
    database = Database(settings)
    session = MagicMock()
    database.sessions = MagicMock(return_value=session)
    session.__enter__.return_value = session
    try:
        try:
            with database.session():
                raise ValueError("fixture")
        except ValueError:
            pass
        session.rollback.assert_called_once()
    finally:
        database.close()


def test_pool_exhaustion_is_not_ready(settings):
    database = Database(settings)
    try:
        with patch.object(database.engine, "connect", side_effect=TimeoutError("private")):
            result = database.readiness()
        assert result["status"] == "not_ready"
        assert result["checks"]["database"] == "busy"
        assert "private" not in str(result)
    finally:
        database.close()


def test_connection_error_is_sanitized(settings):
    database = Database(settings)
    try:
        with patch.object(
            database.engine,
            "connect",
            side_effect=OperationalError("SQL-secret", {}, Exception("password-secret")),
        ):
            result = database.readiness()
        assert result["checks"]["database"] == "unavailable"
        assert "secret" not in str(result)
    finally:
        database.close()


def test_manifest_comes_from_existing_migration_files():
    manifest = expected_history()
    assert set(manifest) == {
        "001_core",
        "002_vectors",
        "003_auth",
        "004_verifier_reports",
        "005_validation",
        "006_teacher_review",
        "007_assessments",
        "008_attempts",
        "009_adaptive",
        "010_feedback",
        "011_analytics",
        "012_evaluation",
        "013_teacher_signup",
    }
    assert (
        manifest["001_core"] == "63429730aa0569c4ac7f2b16d607b74c4da2718fd21ca069af2afcf81ad4a711"
    )
    assert (
        manifest["002_vectors"]
        == "f294ea86a55deab19a5642cf8c37776f75067da3ff253c9ce673bc10ca2292c4"
    )
