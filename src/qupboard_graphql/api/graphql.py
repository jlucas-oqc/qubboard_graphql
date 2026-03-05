"""
GraphQL query resolvers, schema, and FastAPI router.

Strawberry type declarations live in graphql_types.py.
"""

from uuid import UUID

import strawberry
from fastapi import Depends
from sqlalchemy.orm import Session
from strawberry.fastapi import GraphQLRouter
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader

from qupboard_graphql.api.graphql_types import HardwareModel, mapper  # noqa: F401 – mapper.finalize() called there
from qupboard_graphql.db.models import HardwareModelORM
from qupboard_graphql.db.session import get_db


async def get_db_context(db: Session = Depends(get_db)) -> dict:
    """FastAPI dependency that builds the Strawberry request context.

    Provides a SQLAlchemy session and a :class:`StrawberrySQLAlchemyLoader`
    to all GraphQL resolvers via ``info.context``.

    Args:
        db: An active SQLAlchemy session injected by :func:`get_db`.

    Returns:
        A dictionary with ``"db"`` and ``"sqlalchemy_loader"`` keys.
    """
    return {"db": db, "sqlalchemy_loader": StrawberrySQLAlchemyLoader(bind=db)}


@strawberry.type
class Query:
    """Root GraphQL query type exposing hardware-model calibration data."""

    @strawberry.field
    def get_calibration(self, info: strawberry.types.Info, id: UUID) -> HardwareModel | None:
        """Retrieve a single hardware model by its UUID.

        Args:
            info: Strawberry resolver context carrying the database session.
            id: UUID of the hardware model to retrieve.

        Returns:
            The matching :class:`HardwareModel` GraphQL object, or ``None``
            if no record with the given UUID exists.
        """
        db = info.context["db"]
        return HardwareModelORM.get_by_uuid(db, id)

    @strawberry.field
    def get_all_hardware_model_ids(self, info: strawberry.types.Info) -> list[UUID]:
        """Return the UUIDs of all hardware models stored in the database.

        Args:
            info: Strawberry resolver context carrying the database session.

        Returns:
            A list of UUIDs, one per stored hardware model.
        """
        db = info.context["db"]
        return HardwareModelORM.get_all_pks(db)

    @strawberry.field
    def get_all_calibrations(self, info: strawberry.types.Info) -> list[HardwareModel]:
        """Return every hardware model stored in the database.

        Args:
            info: Strawberry resolver context carrying the database session.

        Returns:
            A list of :class:`HardwareModel` GraphQL objects.
        """
        db = info.context["db"]
        return db.query(HardwareModelORM).all()


schema = strawberry.Schema(Query)

graphql_router = GraphQLRouter(schema, context_getter=get_db_context)
