"""
Strawberry GraphQL type declarations, generated from the SQLAlchemy ORM models
via strawberry-sqlalchemy-mapper.

All @mapper.type classes live here so that graphql.py can stay focused on
query resolvers, schema construction, and router wiring.
"""

import json
from uuid import UUID

import strawberry
from sqlalchemy import Uuid as SaUuid
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper

from qupboard_graphql.db.models import (
    CalibratablePulseORM,
    CrossResonanceChannelORM,
    HardwareModelORM,
    PhysicalChannelORM,
    PulseChannelORM,
    QubitORM,
    ResonatorORM,
    ZxPi4CompORM,
)

mapper = StrawberrySQLAlchemyMapper(
    extra_sqlalchemy_type_to_strawberry_type_map={SaUuid: UUID},
)


@mapper.type(PhysicalChannelORM)
class PhysicalChannel:
    """GraphQL type for a physical channel (qubit or resonator).

    The ``qubit`` and ``resonator`` back-references are excluded to avoid
    circular type definitions.
    """

    __exclude__ = ["qubit", "resonator"]


@mapper.type(CalibratablePulseORM)
class CalibratablePulse:
    """GraphQL type for a calibratable pulse waveform."""

    __exclude__ = []


@mapper.type(PulseChannelORM)
class PulseChannel:
    """GraphQL type for a pulse channel (drive, measure, acquire, reset, etc.)."""

    __exclude__ = []


@mapper.type(CrossResonanceChannelORM)
class CrossResonanceChannel:
    """GraphQL type for a cross-resonance or cross-resonance-cancellation channel.

    The ``qubit`` back-reference is excluded to avoid circular type definitions.
    """

    __exclude__ = ["qubit"]


@mapper.type(ZxPi4CompORM)
class ZxPi4Comp:
    """GraphQL type for a ZX-π/4 compensation element.

    The ``qubit`` back-reference is excluded to avoid circular type definitions.
    """

    __exclude__ = ["qubit"]


@mapper.type(ResonatorORM)
class Resonator:
    """GraphQL type for a resonator coupled to a qubit.

    The ``qubit`` back-reference is excluded to avoid circular type definitions.
    """

    __exclude__ = ["qubit"]


@mapper.type(QubitORM)
class Qubit:
    """GraphQL type for a qubit and its associated calibration data.

    The ``hardware_model`` back-reference is excluded to avoid circular type
    definitions.  ``mean_z_map_args`` is resolved from its JSON representation
    via a custom field resolver.
    """

    __exclude__ = ["hardware_model"]

    @strawberry.field
    def mean_z_map_args(self) -> list[float]:
        """Deserialise and return the mean-Z map arguments.

        Returns:
            A list of floats decoded from the JSON-encoded ``mean_z_map_args``
            column stored on the underlying ORM row.
        """
        return json.loads(self.mean_z_map_args)  # type: ignore[attr-defined]


@mapper.type(HardwareModelORM)
class HardwareModel:
    """GraphQL type for the top-level hardware model calibration record."""

    pass


mapper.finalize()
