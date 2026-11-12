"""Validated configuration objects for the OpenRU-X6 simulation lab."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CellConfig(StrictModel):
    name: str = "OpenRU-X6-lab-cell"
    carrier_freq_hz: float = Field(gt=0)
    bandwidth_hz: float = Field(gt=0)
    n_rb_sim: int = Field(ge=1, le=273)
    n_prb: int = Field(ge=1, le=273, default=273)
    resource_mode: Literal["capacity_bound", "nr_grid"] = "nr_grid"
    symbols_per_slot: int = Field(ge=1, le=14, default=14)
    dl_symbols_per_slot: int = Field(ge=1, le=14, default=11)
    tdd_dl_fraction: float = Field(gt=0, le=1, default=0.75)
    control_overhead_fraction: float = Field(ge=0, lt=1, default=0.08)
    dmrs_overhead_fraction: float = Field(ge=0, lt=1, default=0.083)
    ssb_overhead_fraction: float = Field(ge=0, lt=1, default=0.01)
    subcarrier_spacing_hz: float = Field(gt=0)
    slot_duration_s: float = Field(gt=0)
    n_rx_antennas: int = Field(ge=1, le=8)
    noise_figure_db: float
    implementation_margin_db: float = 2.0
    temperature_k: float = Field(gt=0, default=290.0)


class ArrayConfig(StrictModel):
    n_tiles: int = 16
    chains_per_tile: int = 4
    feeds_per_chain: int = 4
    n_feeds: int = 256
    n_chains: int = 64
    tile_rows: int = 4
    tile_cols: int = 4
    site_rows_per_tile: int = 2
    site_cols_per_tile: int = 4
    feeds_per_site: int = 2
    element_spacing_lambda: float
    geometry: str = "planar_yz"
    polarization: str = "dual"
    bearing_deg: float = 0.0
    downtilt_deg: float = 8.0

    @model_validator(mode="after")
    def _check(self) -> "ArrayConfig":
        if self.n_tiles != self.tile_rows * self.tile_cols:
            raise ValueError("n_tiles must equal tile_rows*tile_cols")
        if self.n_chains != self.n_tiles * self.chains_per_tile:
            raise ValueError("n_chains must equal n_tiles*chains_per_tile")
        if self.n_feeds != self.n_chains * self.feeds_per_chain:
            raise ValueError("n_feeds must equal n_chains*feeds_per_chain")
        sites = self.chains_per_tile * self.feeds_per_chain // self.feeds_per_site
        if sites != self.site_rows_per_tile * self.site_cols_per_tile:
            raise ValueError("tile site geometry inconsistent with chains/feeds")
        return self


class MimoConfig(StrictModel):
    max_layers: int = Field(ge=1, le=64)
    precoder: Literal["mf", "zf", "rzf"] = "rzf"
    rzf_alpha: float = Field(ge=0, default=0.01)
    total_tx_power_dbm: float
    per_chain_power_cap_dbm: float
    phase_shifter_bits: int = Field(ge=1, le=8)
    analog_amplitude_error_db: float = 0.0
    analog_phase_error_deg: float = 0.0
    csi_delay_slots: int = Field(ge=0, default=0)
    csi_phase_error_deg: float = 0.0
    csi_amplitude_error_db: float = 0.0
    calibration_phase_error_deg: float = 0.0
    beam_grid_az_deg: float = 120.0
    beam_grid_el_deg: float = 40.0
    beam_grid_points: int = Field(ge=3, default=17)
    rank_threshold: float = Field(gt=0, default=0.05)
    bler_target: float = Field(gt=0, lt=1, default=0.1)
    max_harq_retx: int = Field(ge=0, le=8, default=3)


class ChannelConfig(StrictModel):
    model: str = "geometric_ray"
    n_paths: int = Field(ge=1, le=32)
    los_probability: float = Field(ge=0, le=1)
    shadowing_std_db: float = Field(ge=0)
    nlos_extra_loss_db: float = 0.0
    pathloss_exponent_los: float = 2.0
    pathloss_exponent_nlos: float = 3.3
    angular_spread_deg: float = 8.0
    delay_spread_ns: float = 120.0
    doppler_max_hz: float = 120.0
    min_distance_m: float = 20.0
    max_distance_m: float = 400.0
    bs_height_m: float = 25.0
    ue_height_m: float = 1.5
    indoor_fraction: float = 0.3
    indoor_penetration_db: float = 12.0
    blockage_probability: float = 0.15
    blockage_attenuation_db: float = 25.0


class TrafficConfig(StrictModel):
    model: str = "poisson_bursty"
    mean_arrival_mbps: float = 20.0
    burstiness: float = 2.0
    qos_deadline_slots: int = 40
    queue_max_bits: float = 2.0e7


class PolarizationConfig(StrictModel):
    """Optional dual-polarized channel abstraction.

    ``simple`` preserves the original scalar feed response. ``jones`` uses a
    per-path 2x2 complex polarimetric matrix with XPD/XPR, correlated fading,
    orientation mismatch and calibration errors. This is a behavioural model,
    not measured antenna or PCB polarization data.
    """

    model: Literal["simple", "jones"] = "simple"
    xpd_db: float = 20.0
    xpr_db: float = 20.0
    correlation: float = Field(ge=0, le=1, default=0.5)
    orientation_std_deg: float = Field(ge=0, default=5.0)
    calibration_amplitude_error_db: float = Field(ge=0, default=0.1)
    calibration_phase_error_deg: float = Field(ge=0, default=1.0)


class RadioConfig(StrictModel):
    schema_version: str = "1.0"
    cell: CellConfig
    array: ArrayConfig
    mimo: MimoConfig
    channel: ChannelConfig
    traffic: TrafficConfig
    polarization: PolarizationConfig = Field(default_factory=PolarizationConfig)
    evidence_class: str = "SIMULATED"


class ThermalConfig(StrictModel):
    ambient_c: float = 25.0
    thermal_capacity_j_per_k: float = 900.0
    thermal_resistance_k_per_w: float = 0.45
    fan_resistance_multiplier: float = 1.0
    fan_failure_multiplier: float = 3.0
    throttle_c: float = 80.0
    trip_c: float = 95.0
    hot_spot_delta_c: float = 8.0


class EnergyConfig(StrictModel):
    schema_version: str = "1.0"
    states: dict[str, int]
    always_on_w: float
    dsp_fpga_w: float
    per_chain_electronics_w: float
    per_feed_branch_w: float
    per_tile_control_w: float = 0.3
    pa_efficiency: float
    tx_power_included_in_pa: bool = True
    cooling_fraction_of_dissipation: float
    sleep_standby_w: float
    wakeup_energy_j: float
    wakeup_delay_s: float
    shutdown_delay_s: float
    min_on_dwell_s: float
    min_off_dwell_s: float
    hysteresis_fraction: float
    predictive_horizon_slots: int
    predictive_ewma_alpha: float
    max_switches_per_second: float
    allow_sleep_only_cell: bool
    coverage_requires_min_chains: int
    thermal: ThermalConfig

    @field_validator("states")
    @classmethod
    def _states(cls, v: dict[str, int]) -> dict[str, int]:
        required = {"FULL_64", "BALANCED_32", "ECO_16", "COVERAGE_8", "SLEEP_0"}
        if not required.issubset(v):
            raise ValueError(f"energy states must include {required}")
        if sorted(v.values()) != sorted([0, 8, 16, 32, 64]):
            raise ValueError("energy state chain counts must be 64/32/16/8/0")
        return v


class RoleConfig(StrictModel):
    scopes: list[str]


class SecurityConfig(StrictModel):
    schema_version: str = "1.0"
    clock: dict[str, Any]
    commands: dict[str, Any]
    roles: dict[str, RoleConfig]
    resources: list[str]
    conflict_policy: str = "reject_newer_same_resource_if_pending"
    rollback_on_readback_mismatch: bool = True
    audit_log_hmac: bool = True
    audit_secret_env: str = "OPENRU_AUDIT_SECRET"


class AssumptionItem(StrictModel):
    value: float
    unit: str
    low: float
    high: float
    provenance: str


class PowerAssumptions(StrictModel):
    schema_version: str = "1.0"
    assumptions: dict[str, AssumptionItem]


class ScenarioConfig(StrictModel):
    schema_version: str = "1.0"
    id: str
    title: str
    description: str = ""
    seeds: list[int] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


CONFIG_DIR = Path(os.environ.get("OPENRU_CONFIG_DIR", Path(__file__).resolve().parents[1] / "configs"))


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def load_radio(path: str | Path | None = None) -> RadioConfig:
    return RadioConfig.model_validate(_read_yaml(Path(path) if path else CONFIG_DIR / "radio.yaml"))


def load_energy(path: str | Path | None = None) -> EnergyConfig:
    return EnergyConfig.model_validate(_read_yaml(Path(path) if path else CONFIG_DIR / "energy.yaml"))


def load_security(path: str | Path | None = None) -> SecurityConfig:
    return SecurityConfig.model_validate(_read_yaml(Path(path) if path else CONFIG_DIR / "security.yaml"))


def load_assumptions(path: str | Path | None = None) -> PowerAssumptions:
    return PowerAssumptions.model_validate(_read_yaml(Path(path) if path else CONFIG_DIR / "power.yaml"))


def load_scenario(path: str | Path) -> ScenarioConfig:
    return ScenarioConfig.model_validate(_read_yaml(Path(path)))


def load_scenarios() -> dict[str, ScenarioConfig]:
    out: dict[str, ScenarioConfig] = {}
    for p in sorted((CONFIG_DIR / "scenarios").glob("*.yaml")):
        sc = load_scenario(p)
        out[sc.id] = sc
    return out


def config_digest(*objects: Any) -> str:
    files = []
    if CONFIG_DIR.exists():
        for path in sorted(CONFIG_DIR.rglob("*.yaml")):
            files.append([path.relative_to(CONFIG_DIR).as_posix(),
                          hashlib.sha256(path.read_bytes()).hexdigest()])
    payload = json.dumps(
        [[o.model_dump(mode="json") if hasattr(o, "model_dump") else o for o in objects], files],
        sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:16]
