import pytest

from app import database
from app.main import init_storage


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    import app.main as main

    database.configure_database(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    database.Base.metadata.create_all(database.engine)
    init_storage()
    yield
    database.Base.metadata.drop_all(database.engine)
    database.engine.dispose()
