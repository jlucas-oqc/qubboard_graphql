"""
Pydantic schema hierarchy for a quantum hardware model calibration record.

These schemas are used for request/response validation in the REST API and
as the source of truth for the ORM mapping layer.  The top-level entry point
is :class:`HardwareModel`.

Class hierarchy overview::

    HardwareModel
     └─ qubits: dict[str, Qubit]
           ├─ physical_channel: PhysicalChannel
           │    ├─ baseband: BaseBand
           │    └─ iq_voltage_bias: IQVoltageBias
           ├─ pulse_channels: QubitPulseChannels
           │    ├─ drive: DrivePulseChannel
           │    ├─ second_state: SecondStatePulseChannel
           │    ├─ freq_shift: FreqShiftPulseChannel
           │    ├─ reset: ResetPulseChannel
           │    ├─ cross_resonance_channels: dict[int, CrossResonancePulseChannel]
           │    └─ cross_resonance_cancellation_channels: dict[int, ...]
           ├─ resonator: Resonator
           │    ├─ physical_channel: PhysicalChannel
           │    └─ pulse_channels: ResonatorPulseChannels
           │         ├─ measure: MeasurePulseChannel
           │         ├─ acquire: AcquirePulseChannel
           │         └─ reset: ResetPulseChannel
           ├─ x_pi_2_comp: XPi2Comp
           └─ zx_pi_4_comp: dict[int, ZxPi4Comp]
"""

import math
from uuid import UUID

from pydantic import BaseModel, Field


class Component(BaseModel):
    """Base class for schema objects that carry a UUID identifier.

    Attributes:
        uuid: Unique identifier for this component.
    """

    uuid: UUID


class BaseBand(Component):
    """Baseband oscillator parameters for a physical channel.

    Attributes:
        uuid: Unique identifier inherited from :class:`Component`.
        frequency: Baseband carrier frequency in Hz.
        if_frequency: Intermediate frequency in Hz.
    """

    frequency: float
    if_frequency: float


class IQVoltageBias(BaseModel):
    """IQ voltage bias correction string for a physical channel.

    Attributes:
        bias: Serialised bias value (format is hardware-specific).
    """

    bias: str


class PhysicalChannel(Component):
    """Physical channel connecting a qubit or resonator to the control hardware.

    Attributes:
        uuid: Unique identifier inherited from :class:`Component`.
        name_index: Hardware name index.
        baseband: Associated :class:`BaseBand` oscillator.
        block_size: Waveform block size in samples.
        iq_voltage_bias: IQ voltage bias correction.
        default_amplitude: Default output amplitude (hardware units).
        switch_box: Switch-box identifier string.
        swap_readout_iq: Whether to swap I and Q for readout (resonator only).
    """

    name_index: int
    baseband: BaseBand
    block_size: int
    iq_voltage_bias: IQVoltageBias
    default_amplitude: int
    switch_box: str
    swap_readout_iq: bool = False


class CalibratablePulse(BaseModel):
    """A parameterised pulse waveform used for qubit control.

    Attributes:
        waveform_type: Waveform shape identifier (e.g. ``"gaussian"``).
        width: Pulse duration in seconds.
        amp: Pulse amplitude.
        phase: Pulse phase in radians.
        drag: DRAG correction coefficient.
        rise: Rise-time parameter as a fraction of *width*.
        amp_setup: Setup amplitude.
        std_dev: Gaussian standard deviation in seconds.
    """

    waveform_type: str
    width: float
    amp: float = 0.25 / (100e-9 * 1.0 / 3.0 * math.pi**0.5)
    phase: float = 0.0
    drag: float = 0.0
    rise: float = 1.0 / 3.0
    amp_setup: float = 0.0
    std_dev: float = 0.0


class PulseChannel(Component):
    """Base class for all pulse channels.

    Attributes:
        uuid: Unique identifier inherited from :class:`Component`.
        frequency: Carrier frequency in Hz (``NaN`` when unset).
        imbalance: IQ imbalance correction factor.
        phase_iq_offset: IQ phase offset in radians.
        scale: Complex or real scale factor applied to waveform amplitudes.
    """

    frequency: float = math.nan
    imbalance: float = 1.0
    phase_iq_offset: float = 0.0
    scale: complex | float = 1.0 + 0.0j


class DrivePulseChannel(PulseChannel):
    """Drive pulse channel used to apply single-qubit gates.

    Attributes:
        pulse: Primary X-π/2 drive pulse.
        pulse_x_pi: Optional X-π drive pulse (``None`` when not calibrated).
    """

    pulse: CalibratablePulse
    pulse_x_pi: CalibratablePulse | None


class QubitPulseChannel(PulseChannel):
    """Marker base class for qubit-specific pulse channels."""

    ...


class SecondStatePulseChannel(QubitPulseChannel):
    """Pulse channel for driving the |1⟩→|2⟩ transition.

    Attributes:
        active: Whether second-state driving is enabled.
        delay: Delay before the pulse in seconds.
        pulse: Optional second-state pulse waveform.
    """

    active: bool = False
    delay: float = 0.0
    pulse: CalibratablePulse | None = None


class FreqShiftPulseChannel(QubitPulseChannel):
    """Frequency-shift pulse channel for AC-Stark shift calibration.

    Attributes:
        active: Whether frequency shifting is enabled.
        amp: Frequency-shift amplitude.
        phase: Frequency-shift phase in radians.
    """

    active: bool = False
    amp: float = 1.0
    phase: float = 0.0


class CrossResonancePulseChannel(QubitPulseChannel):
    """Cross-resonance (CR) pulse channel for two-qubit gate calibration.

    Attributes:
        auxiliary_qubit: Index of the auxiliary (target) qubit.
        zx_pi_4_pulse: Optional ZX-π/4 calibration pulse.
    """

    auxiliary_qubit: int
    zx_pi_4_pulse: CalibratablePulse | None


class CrossResonanceCancellationPulseChannel(QubitPulseChannel):
    """Cross-resonance cancellation (CRC) pulse channel.

    Attributes:
        auxiliary_qubit: Index of the auxiliary (target) qubit.
    """

    auxiliary_qubit: int


class ResetPulseChannel(PulseChannel):
    """Reset pulse channel for returning a qubit or resonator to the ground state.

    Attributes:
        delay: Delay before the reset pulse in seconds.
        pulse: Reset pulse waveform.
    """

    delay: float = 0.0
    pulse: CalibratablePulse


class QubitPulseChannels(BaseModel):
    """Container for all pulse channels owned by a single qubit.

    Attributes:
        drive: Drive pulse channel.
        second_state: Second-state pulse channel.
        freq_shift: Frequency-shift pulse channel.
        reset: Qubit reset pulse channel.
        cross_resonance_channels: Mapping of auxiliary-qubit index to
            :class:`CrossResonancePulseChannel`.
        cross_resonance_cancellation_channels: Mapping of auxiliary-qubit index
            to :class:`CrossResonanceCancellationPulseChannel`.
    """

    drive: DrivePulseChannel
    second_state: SecondStatePulseChannel
    freq_shift: FreqShiftPulseChannel
    reset: ResetPulseChannel

    cross_resonance_channels: dict[int, CrossResonancePulseChannel]
    cross_resonance_cancellation_channels: dict[int, CrossResonanceCancellationPulseChannel]


class ResonatorPulseChannel(PulseChannel):
    """Marker base class for resonator-specific pulse channels."""

    ...


class MeasurePulseChannel(ResonatorPulseChannel):
    """Measure pulse channel that drives the readout resonator.

    Attributes:
        pulse: Measurement pulse waveform.
    """

    pulse: CalibratablePulse


class CalibratableAcquire(BaseModel):
    """Acquisition parameters for a readout resonator.

    Attributes:
        delay: Acquisition delay after the measurement pulse in seconds.
        width: Acquisition window width in seconds.
        sync: Whether to synchronise acquisition across multiple channels.
        use_weights: Whether to apply integration weights.
    """

    delay: float = Field(default=180e-08, ge=0)
    width: float = Field(default=1e-06, ge=0)
    sync: bool = True
    use_weights: bool = False


class AcquirePulseChannel(ResonatorPulseChannel):
    """Acquire pulse channel that controls the ADC acquisition window.

    Attributes:
        acquire: Acquisition parameters.
    """

    acquire: CalibratableAcquire = Field(default=CalibratableAcquire(), frozen=True)


class MeasureAcquirePulseChannel(MeasurePulseChannel, AcquirePulseChannel):
    """Combined measure-and-acquire pulse channel retained for backwards compatibility.

    Earlier versions of the schema represented measurement and acquisition as a
    single combined channel.  The current schema separates them into
    :class:`MeasurePulseChannel` and :class:`AcquirePulseChannel` held inside a
    :class:`ResonatorPulseChannels` container.  This class is kept so that
    serialised payloads written against the old schema can still be deserialised;
    it should not be used for new code.
    """

    ...


class ResonatorPulseChannels(BaseModel):
    """Container for all pulse channels owned by a single resonator.

    Attributes:
        measure: Measurement pulse channel.
        acquire: Acquisition pulse channel.
        reset: Resonator reset pulse channel.
    """

    measure: MeasurePulseChannel
    acquire: AcquirePulseChannel
    reset: ResetPulseChannel


class Resonator(Component):
    """Readout resonator coupled to a qubit.

    Attributes:
        uuid: Unique identifier inherited from :class:`Component`.
        physical_channel: Physical channel connected to the resonator.
        pulse_channels: Resonator pulse channels (measure, acquire, reset).
    """

    physical_channel: PhysicalChannel
    pulse_channels: ResonatorPulseChannels


class XPi2Comp(BaseModel):
    """X-π/2 gate phase compensation parameters.

    Attributes:
        phase_comp_x_pi_2: Phase compensation value in radians.
    """

    phase_comp_x_pi_2: float = 0.0


class ZxPi4Comp(BaseModel):
    """ZX-π/4 gate compensation parameters for a single CR pair.

    Attributes:
        pulse_precomp_target_zx_pi_4: Optional pre-compensation pulse.
        pulse_postcomp_target_zx_pi_4: Optional post-compensation pulse.
        phase_comp_target_zx_pi_4: Target ZX-π/4 phase compensation in radians.
        pulse_zx_pi_4_target_rotary_amp: Optional rotary pulse amplitude.
        precomp_active: Whether pre-compensation is enabled.
        postcomp_active: Whether post-compensation is enabled.
        use_second_state: Whether to use the second excited state.
        use_rotary: Whether to use a rotary pulse.
    """

    pulse_precomp_target_zx_pi_4: CalibratablePulse | None = None
    pulse_postcomp_target_zx_pi_4: CalibratablePulse | None = None
    phase_comp_target_zx_pi_4: float = 0.0
    pulse_zx_pi_4_target_rotary_amp: float | None = None
    precomp_active: bool = False
    postcomp_active: bool = False
    use_second_state: bool = False
    use_rotary: bool = False


class Qubit(BaseModel):
    """Full calibration record for a single physical qubit.

    Attributes:
        uuid: Unique identifier for this qubit.
        physical_channel: Physical channel connected to the qubit drive line.
        pulse_channels: All pulse channels owned by this qubit.
        resonator: Coupled readout resonator.
        mean_z_map_args: Two-element list ``[real, imag]`` encoding the mean-Z
            state-discrimination mapping arguments.
        discriminator: Complex or real threshold for state discrimination.
        direct_x_pi: Whether to use a direct X-π pulse instead of two X-π/2
            pulses.
        x_pi_2_comp: X-π/2 gate phase compensation.
        zx_pi_4_comp: Mapping of auxiliary-qubit index to
            :class:`ZxPi4Comp` compensation data.
    """

    uuid: UUID

    physical_channel: PhysicalChannel
    pulse_channels: QubitPulseChannels
    resonator: Resonator

    mean_z_map_args: list[complex | float] = Field(max_length=2, default=[1.0, 0.0])
    discriminator: complex | float = 0.0

    direct_x_pi: bool = False

    x_pi_2_comp: XPi2Comp = Field(default_factory=XPi2Comp)
    zx_pi_4_comp: dict[int, ZxPi4Comp] = Field(default_factory=dict)


class HardwareModel(BaseModel):
    """Top-level hardware model calibration record.

    This is the root schema object serialised to/from JSON for the REST API
    and mapped to/from the :class:`~qupboard_graphql.db.models.HardwareModelORM`
    tree in the database.

    Attributes:
        version: Schema or calibration version string.
        logical_connectivity: Mapping of qubit label to list of neighbour
            indices describing the device topology.
        calibration_id: Identifier for the calibration run.
        qubits: Mapping of qubit key (e.g. ``"q0"``) to :class:`Qubit`.
    """

    version: str
    logical_connectivity: dict[str, list[int]]
    calibration_id: str
    qubits: dict[str, Qubit]
