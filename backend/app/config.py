import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class ConfigurationError(Exception):
    """Safe startup message without submitted configuration values."""


def validate_process_environment():
    if os.getenv("PGSERVICE"):
        raise ConfigurationError(
            "Unset PGSERVICE; the backend uses explicit local database settings."
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
        hide_input_in_errors=True,
        frozen=True,
    )
    app_env: Literal["local", "test"] = "local"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    frontend_origin: str = "http://localhost:5173"
    database_host: str = "127.0.0.1"
    database_port: int = Field(default=5432, ge=1, le=65535)
    database_name: str = Field(default="adaptive_mcq", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
    database_user: str = Field(default="adaptive_mcq_app", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
    database_password: SecretStr
    jwt_secret: SecretStr
    access_token_minutes: int = Field(default=15, ge=5, le=30)
    auth_window_seconds: int = Field(default=900, ge=60, le=3600)
    auth_login_account_limit: int = Field(default=5, ge=3, le=10)
    auth_login_ip_limit: int = Field(default=30, ge=10, le=100)
    auth_register_ip_limit: int = Field(default=5, ge=1, le=20)
    database_pool_size: int = Field(default=2, ge=1, le=4)
    database_pool_timeout_seconds: int = Field(default=2, ge=1, le=5)
    database_connect_timeout_seconds: int = Field(default=3, ge=2, le=5)
    database_statement_timeout_ms: int = Field(default=2000, ge=100, le=5000)
    feedback_min_reporters: int = Field(default=3, ge=1, le=100)
    feedback_report_ratio: float = Field(default=0.2, ge=0, le=1)
    local_only: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    model_selection_status: Literal["pending_hardware_validation"] = "pending_hardware_validation"
    generator_mode: Literal["mock", "disabled", "ollama"] = "mock"
    verifier_mode: Literal["mock", "disabled", "ollama"] = "mock"
    generator_model: str = "qwen2.5:0.5b-instruct-q4_K_M"
    verifier_model: str = "qwen2.5:0.5b-instruct-q4_K_M"
    llm_context_tokens: int = Field(default=2048, ge=512, le=8192)
    llm_output_tokens: int = Field(default=512, ge=64, le=2048)
    llm_max_concurrent_jobs: int = Field(default=1, ge=1, le=1)
    llm_max_regenerations: int = Field(default=2, ge=0, le=3)
    rag_top_k: int = Field(default=3, ge=1, le=8)
    rag_min_similarity: float = Field(default=0.25, ge=0, le=1)
    rag_context_chars: int = Field(default=2400, ge=512, le=6000)
    embedding_model: Literal["sentence-transformers/all-MiniLM-L6-v2"] = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    upload_directory: str = "backend/uploads"
    default_language: Literal["en"] = "en"
    # These fields describe the separately launched Ollama process, not an API call.
    ollama_host: Literal["127.0.0.1:11434"] = "127.0.0.1:11434"
    ollama_no_cloud: bool = True

    @field_validator("api_host", "database_host")
    @classmethod
    def loopback_host(cls, value: str) -> str:
        if value not in LOOPBACK:
            raise ValueError("a loopback host is required")
        return "127.0.0.1" if value == "localhost" else value

    @field_validator("frontend_origin", "ollama_base_url")
    @classmethod
    def loopback_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in LOOPBACK
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or not parsed.port
        ):
            raise ValueError("use an explicit loopback HTTP origin with a port")
        return value.rstrip("/")

    @field_validator("database_password", "jwt_secret")
    @classmethod
    def secret_required(cls, value: SecretStr, info) -> SecretStr:
        plain = value.get_secret_value()
        minimum = 32 if info.field_name == "jwt_secret" else 1
        if len(plain.strip()) < minimum or "\x00" in plain:
            raise ValueError("a nonblank private secret of sufficient length is required")
        return value

    @field_validator("local_only", "ollama_no_cloud")
    @classmethod
    def enforce_local(cls, value: bool) -> bool:
        if not value:
            raise ValueError("the local-only requirement cannot be disabled")
        return value

    @field_validator("generator_model", "verifier_model", "embedding_model")
    @classmethod
    def local_model_name(cls, value: str) -> str:
        if (
            not value.strip()
            or "://" in value
            or any(c.isspace() for c in value)
            or "cloud" in value.lower()
            or "gemini" in value.lower()
        ):
            raise ValueError("a local model identifier is required")
        return value

    @field_validator("upload_directory")
    @classmethod
    def contained_uploads(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or not (PROJECT_ROOT / path).resolve().is_relative_to(PROJECT_ROOT):
            raise ValueError("uploads must be inside this project")
        if path.parts != ("backend", "uploads"):
            raise ValueError("uploads must use backend/uploads")
        return value

    @model_validator(mode="after")
    def token_budget(self):
        if self.llm_output_tokens >= self.llm_context_tokens:
            raise ValueError("output budget must leave space for prompt and context")
        return self


def load_settings(**overrides) -> Settings:
    validate_process_environment()
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        fields = sorted({".".join(map(str, e["loc"])) or "configuration" for e in exc.errors()})
        raise ConfigurationError("Invalid or missing settings: " + ", ".join(fields)) from None
