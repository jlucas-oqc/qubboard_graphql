"""
SQLAlchemy engine and session management for qupboard_graphql.

Provides a shared module-level :class:`~sqlalchemy.engine.Engine` and a
FastAPI-compatible generator dependency that yields a per-request
:class:`~sqlalchemy.orm.Session`.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from qupboard_graphql.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session.

    Opens a new session before each request and ensures it is closed
    afterwards, even if an exception is raised.

    Yields:
        An active :class:`~sqlalchemy.orm.Session` bound to the module engine.
    """
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
