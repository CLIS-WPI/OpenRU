"""Calibration observability models and schematic audit metadata.

The OpenRU-X6 H2 tile provides one complex CAL loopback per RF chain and one
power detector per ADTR1107.  It does not provide a per-feed complex receiver.
This module makes that distinction explicit so calibration software cannot
silently assume sixteen independent IQ observations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .topology import Topology


@dataclass(frozen=True)
class MeasurementArchitecture:
    """Observable calibration quantities and their hardware requirements."""

    name: str
    description: str
    chain_loopback: bool
    per_feed_power: bool
    per_feed_complex: bool
    per_feed_complex_method: str | None
    feed_phase_observable: bool
    chain_phase_observable: bool
    feed_amplitude_observable: bool
    realizable_on_current_h2: bool
    requires_hardware_change: bool
    requires_external_fixture: bool
    chain_cal_phase_error_std_deg: float
    chain_cal_gain_error_std_db: float
    per_feed_complex_phase_error_std_deg: float
    per_feed_complex_gain_error_std_db: float
    power_noise_std_db: float
    notes: str

    def validate(self) -> None:
        if not self.name:
            raise ValueError("architecture name must not be empty")
        if self.per_feed_complex != (self.per_feed_complex_method is not None):
            raise ValueError("per_feed_complex_method must match per_feed_complex")
        if self.feed_phase_observable and not self.per_feed_complex:
            raise ValueError("feed phase requires a per-feed complex measurement")
        for value in (
            self.chain_cal_phase_error_std_deg,
            self.chain_cal_gain_error_std_db,
            self.per_feed_complex_phase_error_std_deg,
            self.per_feed_complex_gain_error_std_db,
            self.power_noise_std_db,
        ):
            if value < 0.0:
                raise ValueError("measurement uncertainty values must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


H2_AVAILABLE = MeasurementArchitecture(
    name="h2_available",
    description=(
        "H2 as drawn: per-chain CAL coupler/combiner loopback plus ADTR1107 "
        "CPLR_OUT power detectors."
    ),
    chain_loopback=True,
    per_feed_power=True,
    per_feed_complex=False,
    per_feed_complex_method=None,
    feed_phase_observable=False,
    chain_phase_observable=True,
    feed_amplitude_observable=True,
    realizable_on_current_h2=True,
    requires_hardware_change=False,
    requires_external_fixture=False,
    chain_cal_phase_error_std_deg=0.5,
    chain_cal_gain_error_std_db=0.05,
    per_feed_complex_phase_error_std_deg=0.0,
    per_feed_complex_gain_error_std_db=0.0,
    power_noise_std_db=0.1,
    notes=(
        "Feeds a common CAL tone into each chain coupler or samples the chain "
        "sum. Per-element phase is not observable."
    ),
)

FACTORY_VNA_FEED_TABLE = MeasurementArchitecture(
    name="factory_vna_feed_table",
    description=(
        "Factory/bench per-feed VNA or reference-receiver table, stored in MCU "
        "memory and applied with chain-level runtime correction."
    ),
    chain_loopback=True,
    per_feed_power=True,
    per_feed_complex=True,
    per_feed_complex_method="factory_vna_or_reference_receiver",
    feed_phase_observable=True,
    chain_phase_observable=True,
    feed_amplitude_observable=True,
    realizable_on_current_h2=True,
    requires_hardware_change=False,
    requires_external_fixture=True,
    chain_cal_phase_error_std_deg=0.5,
    chain_cal_gain_error_std_db=0.05,
    per_feed_complex_phase_error_std_deg=0.3,
    per_feed_complex_gain_error_std_db=0.03,
    power_noise_std_db=0.1,
    notes=(
        "Matches the H1 L1 factory/bench layer. The tile still needs the H2 "
        "runtime CAL loopback for N310 phase after every start or retune."
    ),
)

NEAR_FIELD_PROBE = MeasurementArchitecture(
    name="near_field_probe",
    description=(
        "Shielded near-field/OTA probe, one feed at a time, with other ADAR "
        "channels disabled or terminated."
    ),
    chain_loopback=True,
    per_feed_power=True,
    per_feed_complex=True,
    per_feed_complex_method="near_field_probe_one_feed_at_a_time",
    feed_phase_observable=True,
    chain_phase_observable=True,
    feed_amplitude_observable=True,
    realizable_on_current_h2=True,
    requires_hardware_change=False,
    requires_external_fixture=True,
    chain_cal_phase_error_std_deg=0.5,
    chain_cal_gain_error_std_db=0.05,
    per_feed_complex_phase_error_std_deg=2.0,
    per_feed_complex_gain_error_std_db=0.2,
    power_noise_std_db=0.1,
    notes=(
        "Explicitly called out in cal.kicad_sch. Includes probe positioning "
        "and radiated-coupling error, so it is less accurate than a conducted "
        "per-feed measurement."
    ),
)

PROPOSED_SWITCHED_FEED_LOOPBACK = MeasurementArchitecture(
    name="proposed_switched_feed_loopback",
    description=(
        "Proposed H3 change: per-chain 4:1 switch/combiner from the ADTR1107 "
        "CPLR_OUT ports to a shared complex calibration receiver."
    ),
    chain_loopback=True,
    per_feed_power=True,
    per_feed_complex=True,
    per_feed_complex_method="per_feed_switch_or_combiner_to_complex_receiver",
    feed_phase_observable=True,
    chain_phase_observable=True,
    feed_amplitude_observable=True,
    realizable_on_current_h2=False,
    requires_hardware_change=True,
    requires_external_fixture=False,
    chain_cal_phase_error_std_deg=0.5,
    chain_cal_gain_error_std_db=0.05,
    per_feed_complex_phase_error_std_deg=0.5,
    per_feed_complex_gain_error_std_db=0.05,
    power_noise_std_db=0.1,
    notes=(
        "One feed per chain is connected at a time; switch/combiner paths are "
        "characterized once. Not present on the current H2 schematic."
    ),
)

IDEAL_16IQ = MeasurementArchitecture(
    name="ideal_16iq_nonrealizable",
    description=(
        "Ideal non-realizable comparison: independent complex IQ for every feed "
        "with no calibration-path uncertainty."
    ),
    chain_loopback=True,
    per_feed_power=True,
    per_feed_complex=True,
    per_feed_complex_method="ideal_independent_iq",
    feed_phase_observable=True,
    chain_phase_observable=True,
    feed_amplitude_observable=True,
    realizable_on_current_h2=False,
    requires_hardware_change=True,
    requires_external_fixture=True,
    chain_cal_phase_error_std_deg=0.0,
    chain_cal_gain_error_std_db=0.0,
    per_feed_complex_phase_error_std_deg=0.0,
    per_feed_complex_gain_error_std_db=0.0,
    power_noise_std_db=0.0,
    notes="Baseline only; not an available H2 measurement path.",
)

ARCHITECTURES: dict[str, MeasurementArchitecture] = {
    architecture.name: architecture
    for architecture in (
        H2_AVAILABLE,
        FACTORY_VNA_FEED_TABLE,
        NEAR_FIELD_PROBE,
        PROPOSED_SWITCHED_FEED_LOOPBACK,
        IDEAL_16IQ,
    )
}

DEFAULT_ARCHITECTURES = (
    H2_AVAILABLE.name,
    FACTORY_VNA_FEED_TABLE.name,
    NEAR_FIELD_PROBE.name,
    PROPOSED_SWITCHED_FEED_LOOPBACK.name,
    IDEAL_16IQ.name,
)


def get_architecture(name: str) -> MeasurementArchitecture:
    try:
        architecture = ARCHITECTURES[name]
    except KeyError as error:
        raise ValueError(f"unknown calibration architecture: {name!r}") from error
    architecture.validate()
    return architecture


def identifiability_summary(
    topology: Topology, architecture: MeasurementArchitecture
) -> dict[str, Any]:
    """Return observable and unobservable calibration quantities."""

    architecture.validate()
    return {
        "architecture": architecture.name,
        "n_chains": topology.n_chains,
        "n_feeds": topology.n_feeds,
        "chain_relative_complex_response": architecture.chain_loopback,
        "feed_amplitude": architecture.per_feed_power,
        "feed_phase": architecture.feed_phase_observable,
        "per_feed_complex_response": architecture.per_feed_complex,
        "observable_complex_chain_responses": (
            topology.n_chains if architecture.chain_loopback else 0
        ),
        "observable_feed_power_measurements": (
            topology.n_feeds if architecture.per_feed_power else 0
        ),
        "observable_feed_complex_responses": (
            topology.n_feeds if architecture.per_feed_complex else 0
        ),
        "unidentifiable": (
            []
            if architecture.per_feed_complex
            else [f"feed phase for all {topology.n_feeds} feeds"]
        ),
        "realizable_on_current_h2": architecture.realizable_on_current_h2,
        "requires_hardware_change": architecture.requires_hardware_change,
        "requires_external_fixture": architecture.requires_external_fixture,
    }


def audit_h2_observability(topology: Topology) -> dict[str, Any]:
    """Return the schematic audit and available identifiability model."""

    return {
        "schema_version": "1.0",
        "evidence_label": "SCHEMATIC_AUDIT",
        "hardware_measured": False,
        "topology_name": topology.name,
        "available_architecture": H2_AVAILABLE.to_dict(),
        "identifiability": identifiability_summary(topology, H2_AVAILABLE),
        "supported_architectures": {
            name: identifiability_summary(topology, architecture)
            for name, architecture in ARCHITECTURES.items()
        },
        "findings": [
            {
                "claim": "The H2 tile has a per-chain complex CAL loopback.",
                "status": "confirmed",
                "evidence": [
                    "hardware/H1_CLOCK_CALIBRATION.md: L3 cal coupler on each RF0..RF3 to a 4:1 combiner and CAL SMA.",
                    "hardware/h2/schematics/cal.kicad_sch: J801 'SMA CAL (inject / sample)', U801 EP4RKU+ SUM/P1..P4, CAL_SUM and CAL_INJ1..4.",
                    "hardware/h2/schematics/chain1.kicad_sch: 'cal coupler <-> ADAR1000 UBF1'.",
                ],
            },
            {
                "claim": "The H2 tile does not provide per-feed complex IQ.",
                "status": "confirmed",
                "evidence": [
                    "hardware/h2/schematics/cal.kicad_sch: only CAL_SUM/CAL_INJ1..4 connect to the 4:1 network; there is no per-feed complex receiver.",
                    "hardware/h2/schematics/fe1.kicad_sch: ADTR1107 CPLR_OUT (pin 12) feeds C1_DET1..C1_DET4.",
                    "hardware/h2/schematics/bf1.kicad_sch: C1_DET1..C1_DET4 go to ADAR1000 DET1..DET4.",
                ],
            },
            {
                "claim": "The per-element detectors are power-only.",
                "status": "confirmed",
                "evidence": [
                    "hardware/H1_CLOCK_CALIBRATION.md: ADTR1107 CPLR_OUT to ADAR1000 DET1-4 is amplitude only; detectors cannot do phase calibration.",
                    "hardware/h2/schematics/cal.kicad_sch: 'Per-element: ADTR1107 CPLR_OUT -> ADAR1000 DETx (power only, -20..+10 dBm). Element phase cal needs a near-field/OTA probe in a shielded setup (no OTA at 8.4 GHz).'",
                ],
            },
            {
                "claim": "N310 chain phase is random after every start or retune.",
                "status": "confirmed",
                "evidence": [
                    "hardware/H1_CLOCK_CALIBRATION.md: N310 phase is random between runs; chain-to-chain IF phase must be re-measured at every N310 start/retune.",
                    "hardware/h2/schematics/cal.kicad_sch: 'N310 relative channel phase is random per start/retune -> run CAL-port RX/TX loopback after every N310 init or LO retune.'",
                ],
            },
            {
                "claim": "The H1 L1 feed layer requires a cabled VNA or reference RX per feed.",
                "status": "confirmed",
                "evidence": [
                    "hardware/H1_CLOCK_CALIBRATION.md: L1 feed-to-feed calibration method is 'cabled VNA or reference RX per feed', stored in an MCU table.",
                ],
            },
        ],
        "conclusion": (
            "The current H2 hardware cannot identify 16 independent feed complex "
            "responses. It can identify a relative complex chain common-path "
            "response at the CAL coupler and per-feed amplitude. Feed phase "
            "requires a factory/bench per-feed table, a shielded near-field "
            "probe, or an H3 per-feed switch/combiner."
        ),
    }
