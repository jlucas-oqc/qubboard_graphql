"""
Utilities for converting Pydantic HardwareModel → SQLAlchemy ORM instances.

The public API is :func:`hardware_model_to_orm`.

All private helpers (prefixed ``_``) are internal implementation details.
"""

import json
import math
from uuid import uuid4

from qupboard_graphql.schemas.hardware_model import (
    CalibratablePulse,
    HardwareModel,
    PhysicalChannel,
    Qubit,
    ZxPi4Comp,
)
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


# ---------------------------------------------------------------------------
# Shared helpers (also imported by mapper_from_orm)
# ---------------------------------------------------------------------------


def _scale_parts(scale) -> tuple[float, float]:
    """Return the real and imaginary parts of a scale value.

    Args:
        scale: A :class:`complex` or :class:`float` scale factor.

    Returns:
        A ``(real, imag)`` tuple.  When *scale* is a plain ``float``,
        the imaginary part is ``0.0``.
    """
    if isinstance(scale, complex):
        return scale.real, scale.imag
    return float(scale), 0.0


def _nan_to_none(value: float) -> float | None:
    """Convert a NaN float to ``None`` for SQL NULL storage.

    Args:
        value: The float value to inspect.

    Returns:
        ``None`` if *value* is ``NaN`` or already ``None``; otherwise
        *value* unchanged.
    """
    if value is None:
        return None
    try:
        return None if math.isnan(value) else value
    except (TypeError, ValueError):
        return value


def _none_to_nan(value: float | None) -> float:
    """Convert ``None`` back to NaN when reconstructing Pydantic models.

    Args:
        value: A float or ``None`` read from the database.

    Returns:
        ``math.nan`` when *value* is ``None``; otherwise *value* unchanged.
    """
    return math.nan if value is None else value


# ---------------------------------------------------------------------------
# Pydantic → ORM helpers
# ---------------------------------------------------------------------------


def _pulse_orm(pulse: CalibratablePulse, owner_uuid, pulse_role: str) -> CalibratablePulseORM:
    """Build a :class:`CalibratablePulseORM` from a Pydantic pulse and role metadata.

    Args:
        pulse: The source
            :class:`~qupboard_graphql.schemas.hardware_model.CalibratablePulse`.
        owner_uuid: UUID of the owning channel row.
        pulse_role: Discriminator string identifying which relationship slot
            this pulse fills (e.g. ``"drive"``, ``"drive_x_pi"``, ``"cr"``).

    Returns:
        A new, unsaved :class:`CalibratablePulseORM` instance.
    """
    return CalibratablePulseORM(
        owner_uuid=owner_uuid,
        pulse_role=pulse_role,
        waveform_type=pulse.waveform_type,
        width=pulse.width,
        amp=pulse.amp,
        phase=pulse.phase,
        drag=pulse.drag,
        rise=pulse.rise,
        amp_setup=pulse.amp_setup,
        std_dev=pulse.std_dev,
    )


def _pulse_channel_orm(
    uuid,
    channel_role: str,
    frequency,
    imbalance,
    phase_iq_offset,
    scale,
    qubit_uuid=None,
    resonator_uuid=None,
    **extras,
) -> PulseChannelORM:
    """Build a :class:`PulseChannelORM` row from common fields and role-specific extras.

    Args:
        uuid: UUID for the new pulse channel row.
        channel_role: Role discriminator string
            (e.g. ``"drive"``, ``"acquire"``).
        frequency: Carrier frequency in Hz; ``NaN`` is stored as ``NULL``.
        imbalance: IQ imbalance correction factor.
        phase_iq_offset: IQ phase offset in radians.
        scale: Complex or float scale factor; decomposed into
            ``scale_real`` / ``scale_imag`` columns.
        qubit_uuid: FK to :class:`~qupboard_graphql.db.models.QubitORM`,
            or ``None`` for resonator-owned channels.
        resonator_uuid: FK to
            :class:`~qupboard_graphql.db.models.ResonatorORM`, or ``None``
            for qubit-owned channels.
        **extras: Additional role-specific keyword arguments passed directly
            to the :class:`PulseChannelORM` constructor
            (e.g. ``ss_active``, ``acq_delay``).

    Returns:
        A new, unsaved :class:`PulseChannelORM` instance.
    """
    real, imag = _scale_parts(scale)
    return PulseChannelORM(
        uuid=uuid,
        channel_role=channel_role,
        frequency=_nan_to_none(frequency),
        imbalance=imbalance,
        phase_iq_offset=phase_iq_offset,
        scale_real=real,
        scale_imag=imag,
        qubit_uuid=qubit_uuid,
        resonator_uuid=resonator_uuid,
        **extras,
    )


def _physical_channel_orm(pc: PhysicalChannel, owner_uuid, owner_kind: str) -> PhysicalChannelORM:
    """Build a :class:`PhysicalChannelORM` from a Pydantic :class:`PhysicalChannel`.

    Args:
        pc: The source
            :class:`~qupboard_graphql.schemas.hardware_model.PhysicalChannel`.
        owner_uuid: UUID of the owning qubit or resonator row.
        owner_kind: ``"qubit"`` or ``"resonator"`` — sets ``channel_kind``
            and the appropriate FK column.

    Returns:
        A new, unsaved :class:`PhysicalChannelORM` instance.
    """
    return PhysicalChannelORM(
        uuid=pc.uuid,
        channel_kind=owner_kind,
        name_index=pc.name_index,
        block_size=pc.block_size,
        default_amplitude=pc.default_amplitude,
        switch_box=pc.switch_box,
        swap_readout_iq=pc.swap_readout_iq,
        baseband_uuid=pc.baseband.uuid,
        baseband_frequency=pc.baseband.frequency,
        baseband_if_frequency=pc.baseband.if_frequency,
        iq_bias=pc.iq_voltage_bias.bias,
        qubit_uuid=owner_uuid if owner_kind == "qubit" else None,
        resonator_uuid=owner_uuid if owner_kind == "resonator" else None,
    )


def _zx_pi4_comp_orm(auxiliary_qubit: int, comp: ZxPi4Comp) -> ZxPi4CompORM:
    """Build a :class:`ZxPi4CompORM` from a Pydantic :class:`ZxPi4Comp`.

    Optional pre- and post-compensation pulses are attached as child
    :class:`CalibratablePulseORM` rows when present.

    Args:
        auxiliary_qubit: Index of the auxiliary (control) qubit in the CR pair.
        comp: The source
            :class:`~qupboard_graphql.schemas.hardware_model.ZxPi4Comp`.

    Returns:
        A new, unsaved :class:`ZxPi4CompORM` instance with any child pulses
        already attached.
    """
    orm = ZxPi4CompORM(
        auxiliary_qubit=auxiliary_qubit,
        phase_comp_target_zx_pi_4=comp.phase_comp_target_zx_pi_4,
        pulse_zx_pi_4_target_rotary_amp=comp.pulse_zx_pi_4_target_rotary_amp,
        precomp_active=comp.precomp_active,
        postcomp_active=comp.postcomp_active,
        use_second_state=comp.use_second_state,
        use_rotary=comp.use_rotary,
    )
    if orm.uuid is None:
        orm.uuid = uuid4()
    if comp.pulse_precomp_target_zx_pi_4:
        orm.pulse_precomp = _pulse_orm(comp.pulse_precomp_target_zx_pi_4, orm.uuid, "zx_precomp")
    if comp.pulse_postcomp_target_zx_pi_4:
        orm.pulse_postcomp = _pulse_orm(comp.pulse_postcomp_target_zx_pi_4, orm.uuid, "zx_postcomp")
    return orm


def _qubit_orm(qubit_key: str, qubit: Qubit) -> QubitORM:
    """Convert a Pydantic :class:`Qubit` into a fully-populated :class:`QubitORM` tree.

    Recursively builds all child rows (physical channel, pulse channels,
    resonator, CR/CRC channels, ZX-π/4 comps) and attaches them to the
    returned :class:`QubitORM` via SQLAlchemy relationships.

    Args:
        qubit_key: String key identifying the qubit within the hardware model
            (e.g. ``"q0"``).
        qubit: The source
            :class:`~qupboard_graphql.schemas.hardware_model.Qubit`.

    Returns:
        A new, unsaved :class:`QubitORM` instance with the full child tree
        attached.
    """
    discriminator_real, discriminator_imag = _scale_parts(qubit.discriminator)
    qid = qubit.uuid
    pc = qubit.pulse_channels
    res = qubit.resonator

    # Drive channel
    drive = pc.drive
    drive_orm = _pulse_channel_orm(
        drive.uuid, "drive", drive.frequency, drive.imbalance, drive.phase_iq_offset, drive.scale, qubit_uuid=qid
    )
    drive_orm.pulse = _pulse_orm(drive.pulse, drive.uuid, "drive")
    if drive.pulse_x_pi is not None:
        drive_orm.pulse_x_pi = _pulse_orm(drive.pulse_x_pi, drive.uuid, "drive_x_pi")

    # Second-state channel
    ss = pc.second_state
    ss_orm = _pulse_channel_orm(
        ss.uuid,
        "second_state",
        ss.frequency,
        ss.imbalance,
        ss.phase_iq_offset,
        ss.scale,
        qubit_uuid=qid,
        ss_active=ss.active,
        ss_delay=ss.delay,
    )
    if ss.pulse is not None:
        ss_orm.pulse = _pulse_orm(ss.pulse, ss.uuid, "second_state")

    # Freq-shift channel
    fs = pc.freq_shift
    fs_orm = _pulse_channel_orm(
        fs.uuid,
        "freq_shift",
        fs.frequency,
        fs.imbalance,
        fs.phase_iq_offset,
        fs.scale,
        qubit_uuid=qid,
        fs_active=fs.active,
        fs_amp=fs.amp,
        fs_phase=fs.phase,
    )

    # Qubit reset channel
    qreset = pc.reset
    qreset_orm = _pulse_channel_orm(
        qreset.uuid,
        "reset_qubit",
        qreset.frequency,
        qreset.imbalance,
        qreset.phase_iq_offset,
        qreset.scale,
        qubit_uuid=qid,
        reset_delay=qreset.delay,
    )
    qreset_orm.pulse = _pulse_orm(qreset.pulse, qreset.uuid, "reset_qubit")

    # Resonator
    res_id = res.uuid

    # Measure channel
    mpc = res.pulse_channels.measure
    mpc_orm = _pulse_channel_orm(
        mpc.uuid, "measure", mpc.frequency, mpc.imbalance, mpc.phase_iq_offset, mpc.scale, resonator_uuid=res_id
    )
    mpc_orm.pulse = _pulse_orm(mpc.pulse, mpc.uuid, "measure")

    # Acquire channel
    apc = res.pulse_channels.acquire
    apc_orm = _pulse_channel_orm(
        apc.uuid,
        "acquire",
        apc.frequency,
        apc.imbalance,
        apc.phase_iq_offset,
        apc.scale,
        resonator_uuid=res_id,
        acq_delay=apc.acquire.delay,
        acq_width=apc.acquire.width,
        acq_sync=apc.acquire.sync,
        acq_use_weights=apc.acquire.use_weights,
    )

    # Resonator reset channel
    rreset = res.pulse_channels.reset
    rreset_orm = _pulse_channel_orm(
        rreset.uuid,
        "reset_resonator",
        rreset.frequency,
        rreset.imbalance,
        rreset.phase_iq_offset,
        rreset.scale,
        resonator_uuid=res_id,
        reset_delay=rreset.delay,
    )
    rreset_orm.pulse = _pulse_orm(rreset.pulse, rreset.uuid, "reset_resonator")

    resonator_orm = ResonatorORM(
        uuid=res_id,
        qubit_uuid=qid,
        physical_channel=_physical_channel_orm(res.physical_channel, res_id, "resonator"),
        pulse_channels=[mpc_orm, apc_orm, rreset_orm],
    )

    # CR / CRC channels
    cr_orms = []
    for _, cr in pc.cross_resonance_channels.items():
        cr_real, cr_imag = _scale_parts(cr.scale)
        cr_row = CrossResonanceChannelORM(
            uuid=cr.uuid,
            role="cr",
            auxiliary_qubit=cr.auxiliary_qubit,
            frequency=cr.frequency,
            imbalance=cr.imbalance,
            phase_iq_offset=cr.phase_iq_offset,
            scale_real=cr_real,
            scale_imag=cr_imag,
        )
        if cr.zx_pi_4_pulse is not None:
            cr_row.zx_pi_4_pulse = _pulse_orm(cr.zx_pi_4_pulse, cr.uuid, "cr")
        cr_orms.append(cr_row)

    crc_orms = []
    for _, crc in pc.cross_resonance_cancellation_channels.items():
        crc_real, crc_imag = _scale_parts(crc.scale)
        crc_orms.append(
            CrossResonanceChannelORM(
                uuid=crc.uuid,
                role="crc",
                auxiliary_qubit=crc.auxiliary_qubit,
                frequency=crc.frequency,
                imbalance=crc.imbalance,
                phase_iq_offset=crc.phase_iq_offset,
                scale_real=crc_real,
                scale_imag=crc_imag,
            )
        )

    zx_pi_4_comp_orms = [_zx_pi4_comp_orm(aux, comp) for aux, comp in qubit.zx_pi_4_comp.items()]

    return QubitORM(
        uuid=qid,
        qubit_key=qubit_key,
        mean_z_map_args=json.dumps([v.real if isinstance(v, complex) else v for v in qubit.mean_z_map_args]),
        discriminator_real=discriminator_real,
        discriminator_imag=discriminator_imag,
        direct_x_pi=qubit.direct_x_pi,
        phase_comp_x_pi_2=qubit.x_pi_2_comp.phase_comp_x_pi_2,
        physical_channel=_physical_channel_orm(qubit.physical_channel, qid, "qubit"),
        pulse_channels=[drive_orm, ss_orm, fs_orm, qreset_orm],
        resonator=resonator_orm,
        cross_resonance_channels=cr_orms,
        cross_resonance_cancellation_channels=crc_orms,
        zx_pi_4_comps=zx_pi_4_comp_orms,
    )


def hardware_model_to_orm(model: HardwareModel) -> HardwareModelORM:
    """Convert a validated Pydantic HardwareModel into a fully-populated ORM tree.

    Args:
        model: A validated
            :class:`~qupboard_graphql.schemas.hardware_model.HardwareModel`
            instance.

    Returns:
        A new, unsaved
        :class:`~qupboard_graphql.db.models.HardwareModelORM` instance with
        all child rows attached and ready for ``session.add()`` followed by
        ``session.commit()``.
    """
    qubit_orms = [_qubit_orm(key, qubit) for key, qubit in model.qubits.items()]
    return HardwareModelORM(
        version=model.version,
        calibration_id=model.calibration_id,
        logical_connectivity=json.dumps(model.logical_connectivity),
        qubits=qubit_orms,
    )
