import pytest
from pydantic import ValidationError

from app.settings import Settings


def test_only_luna_is_accepted_as_the_runtime_model():
    with pytest.raises(ValidationError):
        Settings(openai_model="gpt-4.1")


def test_production_requires_a_secure_session_and_postgres():
    settings = Settings(app_env="production", session_secret="production-secret", session_cookie_secure=True, database_url="postgresql+psycopg://prism:prism@db:5432/prism")
    settings.validate_production()

    insecure = Settings(app_env="production", session_secret="production-secret", session_cookie_secure=False, database_url="postgresql+psycopg://prism:prism@db:5432/prism")
    with pytest.raises(ValueError):
        insecure.validate_production()
