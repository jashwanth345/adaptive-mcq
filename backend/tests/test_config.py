from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.config import PROJECT_ROOT, ConfigurationError, Settings, load_settings


def configured(**changes):
    values = {
        "_env_file": None,
        "database_password": "fixture-password",
        "jwt_secret": "fixture-secret-1234567890-1234567890",
    }
    values.update(changes)
    return Settings(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("database_host", "remote.example"),
        ("api_host", "0.0.0.0"),
        ("local_only", False),
        ("ollama_no_cloud", False),
        ("ollama_base_url", "https://api.example.com"),
        ("ollama_base_url", "http://localhost:11434/?secret=abc"),
        ("frontend_origin", "http://localhost.evil:5173"),
        ("frontend_origin", "http://user:pass@localhost:5173"),
        ("database_password", " "),
        ("jwt_secret", "short"),
        ("database_name", "db?host=remote"),
        ("database_user", "owner name"),
        ("llm_max_concurrent_jobs", 2),
        ("llm_output_tokens", 2048),
        ("generator_model", "gemini-3.8-flash"),
        ("verifier_model", "model:cloud"),
        ("upload_directory", "../uploads"),
        ("database_pool_size", 100),
    ],
)
def test_invalid_configuration(field, value):
    with pytest.raises(ValidationError):
        configured(**{field: value})


def test_environment_overrides_project_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "DATABASE_PORT=5440\nDATABASE_PASSWORD=file-fixture\nJWT_SECRET=long-fixture-secret-12345678901234567890\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_PORT", "5441")
    assert Settings(_env_file=env).database_port == 5441


def test_env_template_is_loadable_with_supplied_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_PASSWORD", "supplied-fixture")
    monkeypatch.setenv("JWT_SECRET", "supplied-long-fixture-secret-1234567890")
    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")
    assert settings.llm_max_concurrent_jobs == 1
    assert settings.ollama_no_cloud is True


def test_unknown_dotenv_setting_is_rejected(tmp_path):
    env = tmp_path / ".env"
    env.write_text("DATABASE_PASWORD=typo-secret", encoding="utf-8")
    with pytest.raises(ConfigurationError) as exc:
        load_settings(_env_file=env)
    assert "typo-secret" not in str(exc.value)


def test_safe_startup_error_has_fields_not_secret_values():
    with pytest.raises(ConfigurationError) as exc:
        load_settings(_env_file=None, database_password="private-secret", jwt_secret="bad")
    assert "jwt_secret" in str(exc.value)
    assert "private-secret" not in str(exc.value)
    assert "bad" not in str(exc.value)


def test_model_repr_hides_secrets():
    settings = configured()
    assert "fixture-password" not in repr(settings)
    assert "fixture-secret" not in repr(settings)


def test_default_env_path_is_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Path(Settings.model_config["env_file"]) == PROJECT_ROOT / ".env"


def test_localhost_normalizes_to_numeric_address():
    assert configured(database_host="localhost").database_host == "127.0.0.1"


def test_inherited_service_cannot_override_connection(monkeypatch):
    monkeypatch.setenv("PGSERVICE", "private-cloud-service")
    with pytest.raises(ConfigurationError) as exc:
        load_settings(_env_file=None)
    assert "PGSERVICE" in str(exc.value)
    assert "private-cloud-service" not in str(exc.value)
