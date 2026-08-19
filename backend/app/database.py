"""SQLAlchemy setup for production PostgreSQL persistence."""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def _engine(url: str):
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **options)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


engine = _engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def configure_database(url: str) -> None:
    """Replace the engine for isolated tests or an explicitly configured runtime."""
    global engine, SessionLocal
    engine.dispose()
    engine = _engine(url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
