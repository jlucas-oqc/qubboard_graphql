"""
Repository mixin providing generic primary-key query helpers.

Inherit alongside DeclarativeBase to give ORM models ``get_by_uuid`` and
``get_all_pks`` without cluttering the base class itself.
"""

from typing import Self
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session


class RepositoryMixin:
    """Mixin that adds common primary-key query helpers to SQLAlchemy ORM models.

    Classes that inherit from both :class:`RepositoryMixin` and SQLAlchemy's
    :class:`~sqlalchemy.orm.DeclarativeBase` gain :meth:`get_by_uuid` and
    :meth:`get_all_pks` as class-level helpers without needing a separate
    repository object.
    """

    @classmethod
    def get_by_uuid(cls, session: Session, uuid: UUID) -> Self | None:
        """Return the row whose primary-key column matches *uuid*.

        Args:
            session: An active SQLAlchemy session.
            uuid: The primary-key value to look up.

        Returns:
            The matching ORM instance, or ``None`` if no row is found.

        Raises:
            TypeError: If the model class has no primary key defined.
        """
        pk_cols = inspect(cls).mapper.primary_key
        if not pk_cols:
            raise TypeError(f"{cls.__name__} has no primary key defined")
        pk_col = pk_cols[0]
        return session.query(cls).filter(pk_col == uuid).one_or_none()

    @classmethod
    def get_all_pks(cls, session: Session) -> list:
        """Return a list of all primary key values for this model's table.

        Args:
            session: An active SQLAlchemy session.

        Returns:
            A list containing every primary key value in the table, in
            database-defined order.

        Raises:
            TypeError: If the model class has no primary key defined.
        """
        pk_cols = inspect(cls).mapper.primary_key
        if not pk_cols:
            raise TypeError(f"{cls.__name__} has no primary key defined")
        pk_col = pk_cols[0]
        return [row[0] for row in session.query(pk_col).all()]
