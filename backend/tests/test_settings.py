import pytest

from app.settings import Settings


def test_runtime_model_router_allows_configured_openai_models():
    settings = Settings(luna_model="gpt-5.6-luna", gpt4o_model="gpt-4o", gpt4o_mini_model="gpt-4o-mini")
    assert settings.gpt4o_mini_model == "gpt-4o-mini"


def test_production_requires_a_secure_session_and_postgres():
    settings = Settings(app_env="production", session_secret="production-secret-that-is-long-enough-123", session_cookie_secure=True, database_url="postgresql+psycopg://prism:prism@db:5432/prism")
    settings.validate_production()

    insecure = Settings(app_env="production", session_secret="production-secret-that-is-long-enough-123", session_cookie_secure=False, database_url="postgresql+psycopg://prism:prism@db:5432/prism")
    with pytest.raises(ValueError):
        insecure.validate_production()
