"""
SQLAlchemy engine and session management for qupboard_graphql.

Provides a lazily-initialised shared :class:`~sqlalchemy.engine.Engine` and a
FastAPI-compatible generator dependency that yields a per-request
:class:`~sqlalchemy.orm.Session`.
"""

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from qupboard_graphql.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return the shared SQLAlchemy engine, creating it on the first call.

    The engine is created once (singleton pattern) using the URL from
    :attr:`~qupboard_graphql.config.Settings.DATABASE_URL`.  SQLite's
    ``check_same_thread`` restriction is disabled so that the engine can be
    used safely inside FastAPI's async context.

    Returns:
        The application-wide :class:`~sqlalchemy.engine.Engine` instance.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session.

    Opens a new session before each request and ensures it is closed
    afterwards, even if an exception is raised.

    Yields:
        An active :class:`~sqlalchemy.orm.Session` bound to the shared engine.
    """
    SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
