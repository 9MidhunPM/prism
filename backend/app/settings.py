"""Centralized runtime configuration for PRISM."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "PRISM"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"

    session_secret: SecretStr = SecretStr("development-only-secret")
    session_cookie_secure: bool = False
    session_ttl_seconds: int = Field(default=604800, ge=3600, le=2592000)
    demo_teacher_email: str = "teacher@example.com"
    demo_teacher_password: SecretStr = SecretStr("replace-me")

    database_url: str = "sqlite:///./data/prism.db"

    openai_api_key: SecretStr | None = None
    openai_model: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"
    openai_timeout_seconds: int = Field(default=90, ge=10, le=300)
    openai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_concurrency: int = Field(default=3, ge=1, le=4)
    ai_review_threshold: float = Field(default=0.75, ge=0, le=1)

    s3_endpoint_url: str | None = None
    s3_region: str = "auto"
    s3_bucket: str = "prism-private"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_force_path_style: bool = True
    s3_signed_url_ttl_seconds: int = Field(default=300, ge=30, le=3600)

    max_upload_mb: int = Field(default=20, ge=1, le=100)
    max_submission_pages: int = Field(default=10, ge=1, le=20)
    max_image_dimension: int = Field(default=2400, ge=800, le=5000)
    processed_image_quality: int = Field(default=88, ge=50, le=100)

    job_poll_interval_seconds: int = Field(default=2, ge=1, le=60)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    job_stale_after_seconds: int = Field(default=600, ge=60, le=3600)

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        if not all(origin.startswith(("http://", "https://")) for origin in value.split(",") if origin):
            raise ValueError("CORS_ORIGINS must contain comma-separated HTTP(S) origins")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def openai_enabled(self) -> bool:
        return self.openai_api_key is not None and bool(self.openai_api_key.get_secret_value())

    def validate_production(self) -> None:
        if self.app_env != "production":
            return
        if self.session_secret.get_secret_value() == "development-only-secret":
            raise ValueError("SESSION_SECRET must be set in production")
        if not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true in production")
        if not self.database_url.startswith("postgresql+"):
            raise ValueError("DATABASE_URL must use PostgreSQL in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings
