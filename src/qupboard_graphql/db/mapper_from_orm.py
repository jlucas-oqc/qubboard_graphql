"""
Utilities for converting SQLAlchemy ORM instances → Pydantic HardwareModel.

The public API is :func:`hardware_model_from_orm`.

All private helpers (prefixed ``_``) are internal implementation details.
"""

import json

from qupboard_graphql.schemas.hardware_model import (
    AcquirePulseChannel,
    CalibratableAcquire,
    CalibratablePulse,
    CrossResonanceCancellationPulseChannel,
    CrossResonancePulseChannel,
    DrivePulseChannel,
    FreqShiftPulseChannel,
    HardwareModel,
    MeasurePulseChannel,
    PhysicalChannel,
    Qubit,
    QubitPulseChannels,
    Resonator,
    ResetPulseChannel,
    ResonatorPulseChannels,
    SecondStatePulseChannel,
    XPi2Comp,
    ZxPi4Comp,
)
from qupboard_graphql.db.models import (
    HardwareModelORM,
    PhysicalChannelORM,
    PulseChannelORM,
    QubitORM,
)
from qupboard_graphql.db.mapper_to_orm import _none_to_nan


# ---------------------------------------------------------------------------
# ORM → Pydantic helpers
# ---------------------------------------------------------------------------


def _pulse_from_orm(orm) -> CalibratablePulse:
    """Reconstruct a :class:`CalibratablePulse` from a :class:`CalibratablePulseORM`.

    Args:
        orm: A loaded
            :class:`~qupboard_graphql.db.models.CalibratablePulseORM` row.

    Returns:
        The corresponding Pydantic
        :class:`~qupboard_graphql.schemas.hardware_model.CalibratablePulse`.
    """
    return CalibratablePulse(
        waveform_type=orm.waveform_type,
        width=orm.width,
        amp=orm.amp,
        phase=orm.phase,
        drag=orm.drag,
        rise=orm.rise,
        amp_setup=orm.amp_setup,
        std_dev=orm.std_dev,
    )


def _physical_channel_from_orm(orm: PhysicalChannelORM) -> PhysicalChannel:
    """Reconstruct a :class:`PhysicalChannel` from a :class:`PhysicalChannelORM`.

    Args:
        orm: A loaded
            :class:`~qupboard_graphql.db.models.PhysicalChannelORM` row.

    Returns:
        The corresponding Pydantic
        :class:`~qupboard_graphql.schemas.hardware_model.PhysicalChannel`.
    """
    from qupboard_graphql.schemas.hardware_model import BaseBand, IQVoltageBias

    return PhysicalChannel(
        uuid=orm.id,
        name_index=orm.name_index,
        block_size=orm.block_size,
        default_amplitude=orm.default_amplitude,
        switch_box=orm.switch_box,
        swap_readout_iq=orm.swap_readout_iq,
        baseband=BaseBand(
            uuid=orm.baseband_uuid,
            frequency=orm.baseband_frequency,
            if_frequency=orm.baseband_if_frequency,
        ),
        iq_voltage_bias=IQVoltageBias(bias=orm.iq_bias),
    )


def _reset_pulse_channel_from_orm(orm: PulseChannelORM) -> ResetPulseChannel:
    """Reconstruct a :class:`ResetPulseChannel` from a :class:`PulseChannelORM`.

    Args:
        orm: A loaded
            :class:`~qupboard_graphql.db.models.PulseChannelORM` row with
            ``channel_role`` equal to ``"reset_qubit"`` or
            ``"reset_resonator"``.

    Returns:
        The corresponding Pydantic
        :class:`~qupboard_graphql.schemas.hardware_model.ResetPulseChannel`.
    """
    return ResetPulseChannel(
        uuid=orm.id,
        frequency=_none_to_nan(orm.frequency),
        imbalance=orm.imbalance,
        phase_iq_offset=orm.phase_iq_offset,
        scale=complex(orm.scale_real, orm.scale_imag),
        delay=orm.reset_delay,
        pulse=_pulse_from_orm(orm.pulse),
    )


def _qubit_from_orm(orm: QubitORM) -> tuple[str, Qubit]:
    """Reconstruct a ``(qubit_key, Qubit)`` pair from a :class:`QubitORM`.

    Recursively reconstructs all nested Pydantic objects from their ORM
    counterparts (physical channels, pulse channels, resonator, CR/CRC
    channels, ZX-π/4 comps).

    Args:
        orm: A fully-loaded
            :class:`~qupboard_graphql.db.models.QubitORM` row.

    Returns:
        A ``(qubit_key, qubit)`` tuple where *qubit_key* is the string key
        used in the parent
        :class:`~qupboard_graphql.schemas.hardware_model.HardwareModel`'s
        ``qubits`` mapping and *qubit* is the reconstructed
        :class:`~qupboard_graphql.schemas.hardware_model.Qubit`.
    """
    mean_z = json.loads(orm.mean_z_map_args)
    discriminator = complex(orm.discriminator_real, orm.discriminator_imag)

    qubit_pc = _physical_channel_from_orm(orm.physical_channel)
    res_pc = _physical_channel_from_orm(orm.resonator.physical_channel)

    drive = orm.drive_channel
    ss = orm.second_state_channel
    fs = orm.freq_shift_channel
    mpc = orm.resonator.measure_channel
    apc = orm.resonator.acquire_channel

    cross_resonance = {
        cr.auxiliary_qubit: CrossResonancePulseChannel(
            uuid=cr.id,
            auxiliary_qubit=cr.auxiliary_qubit,
            frequency=_none_to_nan(cr.frequency),
            imbalance=cr.imbalance,
            phase_iq_offset=cr.phase_iq_offset,
            scale=complex(cr.scale_real, cr.scale_imag),
            zx_pi_4_pulse=_pulse_from_orm(cr.zx_pi_4_pulse) if cr.zx_pi_4_pulse else None,
        )
        for cr in orm.cross_resonance_channels
    }
    cross_resonance_cancellation = {
        crc.auxiliary_qubit: CrossResonanceCancellationPulseChannel(
            uuid=crc.id,
            auxiliary_qubit=crc.auxiliary_qubit,
            frequency=_none_to_nan(crc.frequency),
            imbalance=crc.imbalance,
            phase_iq_offset=crc.phase_iq_offset,
            scale=complex(crc.scale_real, crc.scale_imag),
        )
        for crc in orm.cross_resonance_cancellation_channels
    }

    pulse_channels = QubitPulseChannels(
        drive=DrivePulseChannel(
            uuid=drive.id,
            frequency=_none_to_nan(drive.frequency),
            imbalance=drive.imbalance,
            phase_iq_offset=drive.phase_iq_offset,
            scale=complex(drive.scale_real, drive.scale_imag),
            pulse=_pulse_from_orm(drive.pulse),
            pulse_x_pi=_pulse_from_orm(drive.pulse_x_pi) if drive.pulse_x_pi else None,
        ),
        second_state=SecondStatePulseChannel(
            uuid=ss.id,
            frequency=_none_to_nan(ss.frequency),
            imbalance=ss.imbalance,
            phase_iq_offset=ss.phase_iq_offset,
            scale=complex(ss.scale_real, ss.scale_imag),
            active=ss.ss_active,
            delay=ss.ss_delay,
            pulse=_pulse_from_orm(ss.pulse) if ss.pulse else None,
        ),
        freq_shift=FreqShiftPulseChannel(
            uuid=fs.id,
            frequency=_none_to_nan(fs.frequency),
            imbalance=fs.imbalance,
            phase_iq_offset=fs.phase_iq_offset,
            scale=complex(fs.scale_real, fs.scale_imag),
            active=fs.fs_active,
            amp=fs.fs_amp,
            phase=fs.fs_phase,
        ),
        reset=_reset_pulse_channel_from_orm(orm.reset_qubit_channel),
        cross_resonance_channels=cross_resonance,
        cross_resonance_cancellation_channels=cross_resonance_cancellation,
    )

    resonator = Resonator(
        uuid=orm.resonator.id,
        physical_channel=res_pc,
        pulse_channels=ResonatorPulseChannels(
            measure=MeasurePulseChannel(
                uuid=mpc.id,
                frequency=_none_to_nan(mpc.frequency),
                imbalance=mpc.imbalance,
                phase_iq_offset=mpc.phase_iq_offset,
                scale=complex(mpc.scale_real, mpc.scale_imag),
                pulse=_pulse_from_orm(mpc.pulse),
            ),
            acquire=AcquirePulseChannel(
                uuid=apc.id,
                frequency=_none_to_nan(apc.frequency),
                imbalance=apc.imbalance,
                phase_iq_offset=apc.phase_iq_offset,
                scale=complex(apc.scale_real, apc.scale_imag),
                acquire=CalibratableAcquire(
                    delay=apc.acq_delay,
                    width=apc.acq_width,
                    sync=apc.acq_sync,
                    use_weights=apc.acq_use_weights,
                ),
            ),
            reset=_reset_pulse_channel_from_orm(orm.resonator.reset_resonator_channel),
        ),
    )

    zx_pi_4_comp = {
        comp.auxiliary_qubit: ZxPi4Comp(
            pulse_precomp_target_zx_pi_4=_pulse_from_orm(comp.pulse_precomp) if comp.pulse_precomp else None,
            pulse_postcomp_target_zx_pi_4=_pulse_from_orm(comp.pulse_postcomp) if comp.pulse_postcomp else None,
            phase_comp_target_zx_pi_4=comp.phase_comp_target_zx_pi_4,
            pulse_zx_pi_4_target_rotary_amp=comp.pulse_zx_pi_4_target_rotary_amp,
            precomp_active=comp.precomp_active,
            postcomp_active=comp.postcomp_active,
            use_second_state=comp.use_second_state,
            use_rotary=comp.use_rotary,
        )
        for comp in orm.zx_pi_4_comps
    }

    return orm.qubit_key, Qubit(
        uuid=orm.id,
        physical_channel=qubit_pc,
        pulse_channels=pulse_channels,
        resonator=resonator,
        mean_z_map_args=mean_z,
        discriminator=discriminator,
        direct_x_pi=orm.direct_x_pi,
        x_pi_2_comp=XPi2Comp(phase_comp_x_pi_2=orm.phase_comp_x_pi_2),
        zx_pi_4_comp=zx_pi_4_comp,
    )


def hardware_model_from_orm(orm: HardwareModelORM) -> HardwareModel:
    """Convert a fully-loaded ORM HardwareModelORM back into a Pydantic HardwareModel.

    Args:
        orm: A fully-loaded
            :class:`~qupboard_graphql.db.models.HardwareModelORM` instance
            (all relationships must be accessible).

    Returns:
        The reconstructed
        :class:`~qupboard_graphql.schemas.hardware_model.HardwareModel`
        instance.
    """
    qubits = dict(_qubit_from_orm(q) for q in orm.qubits)
    return HardwareModel(
        version=orm.version,
        calibration_id=orm.calibration_id,
        logical_connectivity=json.loads(orm.logical_connectivity),
        qubits=qubits,
    )
