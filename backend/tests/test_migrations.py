from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_fresh_database_upgrades_through_all_migrations(tmp_path):
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    database_path = tmp_path / "fresh.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    config.attributes["use_config_url"] = True
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path}")
    columns = {column["name"] for column in inspect(engine).get_columns("criterion_evaluations")}
    assert "review_severity" in columns
