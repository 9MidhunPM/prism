"""Run Alembic migrations with a singleton PostgreSQL lock."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from .settings import get_settings


def main() -> None:
    settings = get_settings()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        is_postgres = connection.dialect.name == "postgresql"
        if is_postgres:
            connection.execute(text("SELECT pg_advisory_lock(hashtext('prism_schema_migration'))"))
        try:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if is_postgres:
                connection.execute(text("SELECT pg_advisory_unlock(hashtext('prism_schema_migration'))"))
    engine.dispose()


if __name__ == "__main__":
    main()
