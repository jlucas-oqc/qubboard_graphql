"""
SQLAlchemy declarative base for all ORM models in qupboard_graphql.

All ORM model classes inherit from :class:`Base` so that
``Base.metadata`` tracks the full table schema and can drive
Alembic migrations and table creation.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""

    pass
