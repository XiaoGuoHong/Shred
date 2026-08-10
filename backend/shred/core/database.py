"""Database engine and request-session helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from shred.core.config import get_env_settings


def create_engine_for_url(url: str) -> Engine:
    """Create an engine with SQLite foreign keys enabled on every connection."""
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions that retain loaded values after request completion."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


engine = create_engine_for_url(get_env_settings().database_url)
SessionLocal = create_session_factory(engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a session for a request and close it when the request finishes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
