"""
Utilities for converting Pydantic HardwareModel → SQLAlchemy ORM instances.

The public API is :func:`hardware_model_to_orm`.

All private helpers (prefixed ``_``) are internal implementation details.
"""

import json
import math

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


def _pulse_orm(pulse: CalibratablePulse, pulse_role: str) -> CalibratablePulseORM:
    """Build a :class:`CalibratablePulseORM` from a Pydantic pulse and role metadata.

    Args:
        pulse: The source
            :class:`~qupboard_graphql.schemas.hardware_model.CalibratablePulse`.
        pulse_role: Discriminator string identifying which relationship slot
            this pulse fills (e.g. ``"drive"``, ``"drive_x_pi"``, ``"cr"``).

    Returns:
        A new, unsaved :class:`CalibratablePulseORM` instance.
    """
    return CalibratablePulseORM(
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
    channel_id,
    channel_role: str,
    frequency,
    imbalance,
    phase_iq_offset,
    scale,
    **extras,
) -> PulseChannelORM:
    """Build a :class:`PulseChannelORM` row from common fields and role-specific extras.

    Args:
        channel_id: UUID used as the pulse channel primary key.
        channel_role: Role discriminator string
            (e.g. ``"drive"``, ``"acquire"``).
        frequency: Carrier frequency in Hz; ``NaN`` is stored as ``NULL``.
        imbalance: IQ imbalance correction factor.
        phase_iq_offset: IQ phase offset in radians.
        scale: Complex or float scale factor; decomposed into
            ``scale_real`` / ``scale_imag`` columns.
        **extras: Additional role-specific keyword arguments passed directly
            to the :class:`PulseChannelORM` constructor
            (e.g. ``ss_active``, ``acq_delay``).

    Returns:
        A new, unsaved :class:`PulseChannelORM` instance.
    """
    real, imag = _scale_parts(scale)
    return PulseChannelORM(
        id=channel_id,
        channel_role=channel_role,
        frequency=_nan_to_none(frequency),
        imbalance=imbalance,
        phase_iq_offset=phase_iq_offset,
        scale_real=real,
        scale_imag=imag,
        **extras,
    )


def _physical_channel_orm(pc: PhysicalChannel, owner_kind: str) -> PhysicalChannelORM:
    """Build a :class:`PhysicalChannelORM` from a Pydantic :class:`PhysicalChannel`.

    Args:
        pc: The source
            :class:`~qupboard_graphql.schemas.hardware_model.PhysicalChannel`.
        owner_kind: ``"qubit"`` or ``"resonator"`` — sets ``channel_kind``
            discriminator.

    Returns:
        A new, unsaved :class:`PhysicalChannelORM` instance.
    """
    return PhysicalChannelORM(
        id=pc.uuid,
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
    if comp.pulse_precomp_target_zx_pi_4:
        orm.pulse_precomp = _pulse_orm(comp.pulse_precomp_target_zx_pi_4, "zx_precomp")
    if comp.pulse_postcomp_target_zx_pi_4:
        orm.pulse_postcomp = _pulse_orm(comp.pulse_postcomp_target_zx_pi_4, "zx_postcomp")
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
    pc = qubit.pulse_channels
    res = qubit.resonator

    # Drive channel
    drive = pc.drive
    drive_orm = _pulse_channel_from_schema(drive, "drive")
    drive_orm.pulse = _pulse_orm(drive.pulse, "drive")
    if drive.pulse_x_pi is not None:
        drive_orm.pulse_x_pi = _pulse_orm(drive.pulse_x_pi, "drive_x_pi")

    # Second-state channel
    ss = pc.second_state
    ss_orm = _pulse_channel_from_schema(
        ss,
        "second_state",
        ss_active=ss.active,
        ss_delay=ss.delay,
    )
    if ss.pulse is not None:
        ss_orm.pulse = _pulse_orm(ss.pulse, "second_state")

    # Freq-shift channel
    fs = pc.freq_shift
    fs_orm = _pulse_channel_from_schema(
        fs,
        "freq_shift",
        fs_active=fs.active,
        fs_amp=fs.amp,
        fs_phase=fs.phase,
    )

    # Qubit reset channel
    qreset = pc.reset
    qreset_orm = _pulse_channel_from_schema(
        qreset,
        "reset_qubit",
        reset_delay=qreset.delay,
    )
    qreset_orm.pulse = _pulse_orm(qreset.pulse, "reset_qubit")

    # Resonator

    # Measure channel
    mpc = res.pulse_channels.measure
    mpc_orm = _pulse_channel_from_schema(mpc, "measure")
    mpc_orm.pulse = _pulse_orm(mpc.pulse, "measure")

    # Acquire channel
    apc = res.pulse_channels.acquire
    apc_orm = _pulse_channel_from_schema(
        apc,
        "acquire",
        acq_delay=apc.acquire.delay,
        acq_width=apc.acquire.width,
        acq_sync=apc.acquire.sync,
        acq_use_weights=apc.acquire.use_weights,
    )

    # Resonator reset channel
    rreset = res.pulse_channels.reset
    rreset_orm = _pulse_channel_from_schema(
        rreset,
        "reset_resonator",
        reset_delay=rreset.delay,
    )
    rreset_orm.pulse = _pulse_orm(rreset.pulse, "reset_resonator")

    resonator_orm = ResonatorORM(
        id=res.uuid,
        physical_channel=_physical_channel_orm(res.physical_channel, "resonator"),
        pulse_channels=[mpc_orm, apc_orm, rreset_orm],
    )

    # CR / CRC channels
    cr_orms = []
    for _, cr in pc.cross_resonance_channels.items():
        cr_row = _cross_resonance_channel_orm(cr, "cr")
        if cr.zx_pi_4_pulse is not None:
            cr_row.zx_pi_4_pulse = _pulse_orm(cr.zx_pi_4_pulse, "cr")
        cr_orms.append(cr_row)

    crc_orms = [_cross_resonance_channel_orm(crc, "crc") for _, crc in pc.cross_resonance_cancellation_channels.items()]

    zx_pi_4_comp_orms = [_zx_pi4_comp_orm(aux, comp) for aux, comp in qubit.zx_pi_4_comp.items()]

    return QubitORM(
        id=qubit.uuid,
        qubit_key=qubit_key,
        mean_z_map_args=json.dumps([v.real if isinstance(v, complex) else v for v in qubit.mean_z_map_args]),
        discriminator_real=discriminator_real,
        discriminator_imag=discriminator_imag,
        direct_x_pi=qubit.direct_x_pi,
        phase_comp_x_pi_2=qubit.x_pi_2_comp.phase_comp_x_pi_2,
        physical_channel=_physical_channel_orm(qubit.physical_channel, "qubit"),
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


def _pulse_channel_from_schema(channel, channel_role: str, **extras) -> PulseChannelORM:
    """Build a PulseChannelORM from a schema channel sharing common fields."""
    return _pulse_channel_orm(
        channel.uuid,
        channel_role,
        channel.frequency,
        channel.imbalance,
        channel.phase_iq_offset,
        channel.scale,
        **extras,
    )


def _cross_resonance_channel_orm(channel, role: str) -> CrossResonanceChannelORM:
    """Build a CR/CRC ORM row from a schema cross-resonance channel."""
    real, imag = _scale_parts(channel.scale)
    return CrossResonanceChannelORM(
        id=channel.uuid,
        role=role,
        auxiliary_qubit=channel.auxiliary_qubit,
        frequency=channel.frequency,
        imbalance=channel.imbalance,
        phase_iq_offset=channel.phase_iq_offset,
        scale_real=real,
        scale_imag=imag,
    )
