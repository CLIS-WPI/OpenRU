"""RF geometry, feed/chain/tile mapping, analog beamforming and hardware state.

Units: positions in metres, frequencies in Hz, powers in dBm/W, phases in radians
unless a field name says otherwise.  This is a behavioural RF abstraction, not an
electromagnetic or circuit simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .config import ArrayConfig

C_LIGHT = 299_792_458.0


@dataclass(frozen=True)
class FeedMap:
    feed_positions: np.ndarray      # [F,3] metres
    feed_tile: np.ndarray           # [F]
    feed_chain: np.ndarray          # [F]
    feed_pol: np.ndarray            # [F] 0=V, 1=H
    feed_site: np.ndarray           # [F]
    chain_tile: np.ndarray          # [C]
    site_tile: np.ndarray           # [S]
    tile_rows: int
    tile_cols: int
    site_rows: int
    site_cols: int
    wavelength_m: float

    @property
    def n_feeds(self) -> int:
        return int(self.feed_positions.shape[0])

    @property
    def n_chains(self) -> int:
        return int(self.chain_tile.shape[0])

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.n_feeds != 256:
            errs.append(f"expected 256 feeds, got {self.n_feeds}")
        if self.n_chains != 64:
            errs.append(f"expected 64 chains, got {self.n_chains}")
        for c in range(self.n_chains):
            n = int(np.sum(self.feed_chain == c))
            if n != 4:
                errs.append(f"chain {c} drives {n} feeds (expected 4)")
        for f in range(self.n_feeds):
            if int(self.feed_chain[f]) not in range(self.n_chains):
                errs.append(f"feed {f} unmapped")
        if set(self.feed_tile.tolist()) != set(range(16)):
            errs.append("tile set is not exactly 0..15")
        # disjoint feed ownership
        if len(set(self.feed_chain.tolist())) != self.n_chains:
            errs.append("chain ownership incomplete")
        return errs


def build_feed_map(cfg: ArrayConfig, carrier_freq_hz: float) -> FeedMap:
    lam = C_LIGHT / carrier_freq_hz
    d = cfg.element_spacing_lambda * lam
    site_rows = cfg.tile_rows * cfg.site_rows_per_tile
    site_cols = cfg.tile_cols * cfg.site_cols_per_tile
    sites: list[tuple[float, float, int, int]] = []
    positions: list[tuple[float, float, float]] = []
    feed_tile: list[int] = []
    feed_chain: list[int] = []
    feed_pol: list[int] = []
    feed_site: list[int] = []
    chain_tile = np.repeat(np.arange(cfg.n_tiles), cfg.chains_per_tile)
    site_tile = np.zeros(site_rows * site_cols, dtype=int)
    for gy in range(site_rows):
        for gx in range(site_cols):
            s = gy * site_cols + gx
            tile = (gy // cfg.site_rows_per_tile) * cfg.tile_cols + (gx // cfg.site_cols_per_tile)
            site_tile[s] = tile
            y = (gx - (site_cols - 1) / 2.0) * d
            z = (gy - (site_rows - 1) / 2.0) * d
            sites.append((y, z, tile, s))
            local_row = gy % cfg.site_rows_per_tile
            local_col = gx % cfg.site_cols_per_tile
            local_site = local_row * cfg.site_cols_per_tile + local_col
            chain = tile * cfg.chains_per_tile + local_site // (cfg.feeds_per_chain // cfg.feeds_per_site)
            for pol in range(cfg.feeds_per_site):
                positions.append((0.0, y, z))
                feed_tile.append(tile)
                feed_chain.append(chain)
                feed_pol.append(pol)
                feed_site.append(s)
    fm = FeedMap(
        feed_positions=np.asarray(positions, dtype=np.float64),
        feed_tile=np.asarray(feed_tile, dtype=int),
        feed_chain=np.asarray(feed_chain, dtype=int),
        feed_pol=np.asarray(feed_pol, dtype=int),
        feed_site=np.asarray(feed_site, dtype=int),
        chain_tile=chain_tile.astype(int),
        site_tile=site_tile,
        tile_rows=cfg.tile_rows, tile_cols=cfg.tile_cols,
        site_rows=site_rows, site_cols=site_cols, wavelength_m=lam,
    )
    errs = fm.validate()
    if errs:
        raise ValueError("invalid RF map: " + "; ".join(errs))
    return fm


def direction_from_angles(az_deg: np.ndarray | float, el_deg: np.ndarray | float) -> np.ndarray:
    """Unit vector with azimuth measured from +x toward +y and elevation from the y-z plane."""
    az = np.deg2rad(np.asarray(az_deg, dtype=np.float64))
    el = np.deg2rad(np.asarray(el_deg, dtype=np.float64))
    u = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], axis=-1)
    return u


def array_response(fm: FeedMap, directions: np.ndarray) -> np.ndarray:
    """Complex feed response [..., F] for unit direction vectors [..., 3]."""
    u = np.asarray(directions, dtype=np.float64)
    k = 2.0 * np.pi / fm.wavelength_m
    proj = fm.feed_positions[:, 1] * u[..., None, 1] + fm.feed_positions[:, 2] * u[..., None, 2]
    phase = k * proj
    pol = np.where(fm.feed_pol == 0, 1.0 + 0j, 1j)
    return np.exp(1j * phase) * pol


def quantize_phase(phi: np.ndarray, bits: int) -> np.ndarray:
    step = 2.0 * np.pi / (2 ** bits)
    return np.round(np.asarray(phi) / step) * step


@dataclass
class RFHardware:
    """Behavioural RF state shared by the beamformer, control plane and telemetry."""

    cfg: ArrayConfig
    fm: FeedMap
    tile_enabled: np.ndarray = field(init=False)
    chain_enabled: np.ndarray = field(init=False)
    chain_gain_db: np.ndarray = field(init=False)
    chain_phase_deg: np.ndarray = field(init=False)
    chain_vswr: np.ndarray = field(init=False)
    chain_noise_fig_db: np.ndarray = field(init=False)
    tile_temp_c: np.ndarray = field(init=False)
    tile_supply_v: np.ndarray = field(init=False)
    tile_ptp_offset_ns: np.ndarray = field(init=False)
    tile_isolated: np.ndarray = field(init=False)
    calibration_epoch: int = 0
    fan_ok: bool = True
    tx_power_limit_dbm: float | None = None
    protection_latched: bool = False
    telemetry_seed: int | None = None
    last_readback: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = self.fm.n_chains
        self.tile_enabled = np.ones(self.cfg.n_tiles, dtype=bool)
        self.chain_enabled = np.ones(n, dtype=bool)
        self.chain_gain_db = np.zeros(n)
        self.chain_phase_deg = np.zeros(n)
        self.chain_vswr = np.full(n, 1.2)
        self.chain_noise_fig_db = np.zeros(n)
        self.tile_temp_c = np.full(self.cfg.n_tiles, 32.0)
        self.tile_supply_v = np.full(self.cfg.n_tiles, 48.0)
        self.tile_ptp_offset_ns = np.zeros(self.cfg.n_tiles)
        self.tile_isolated = np.zeros(self.cfg.n_tiles, dtype=bool)
        # Every hardware instance needs its own sensor-noise stream.  The seed
        # is supplied by the run/calibration context when reproducibility is
        # required; otherwise the OS entropy source is used.
        self._telemetry_rng = np.random.default_rng(self.telemetry_seed)
        self._telemetry_drift = np.zeros((self.cfg.n_tiles, 9))
        self._telemetry_drift_scale = np.array(
            [0.005, 0.003, 0.01, 0.0005, 0.005, 0.001, 0.02, 0.005, 0.0])

    # ---- masks -----------------------------------------------------------
    def set_tile_mask(self, mask: np.ndarray) -> None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != (self.cfg.n_tiles,):
            raise ValueError("tile mask must have 16 entries")
        self.tile_enabled = mask
        self.chain_enabled = mask[self.fm.chain_tile].copy()

    def set_chain_mask(self, mask: np.ndarray) -> None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != (self.fm.n_chains,):
            raise ValueError("chain mask must have 64 entries")
        self.chain_enabled = mask.copy()
        for t in range(self.cfg.n_tiles):
            self.tile_enabled[t] = bool(np.any(mask[self.fm.chain_tile == t]))

    def active_chains(self) -> int:
        return int(np.sum(self.chain_enabled))

    def active_feeds(self) -> np.ndarray:
        return self.chain_enabled[self.fm.feed_chain]

    def isolate_tile(self, tile: int) -> None:
        self.tile_isolated[tile] = True
        self.tile_enabled[tile] = False
        self.chain_enabled[self.fm.chain_tile == tile] = False
        self.chain_gain_db[self.fm.chain_tile == tile] = -40.0

    def restore_tile(self, tile: int) -> None:
        self.tile_isolated[tile] = False
        self.tile_enabled[tile] = True
        self.chain_enabled[self.fm.chain_tile == tile] = True
        self.chain_gain_db[self.fm.chain_tile == tile] = 0.0
        self.chain_phase_deg[self.fm.chain_tile == tile] = 0.0

    def mask_to_state_name(self) -> str:
        n = self.active_chains()
        try:
            from .energy import STATE_BY_CHAINS
            return STATE_BY_CHAINS.get(n, f"CUSTOM_{n}")
        except Exception:
            return f"CUSTOM_{n}"

    # ---- analog weights --------------------------------------------------
    def analog_weights(self, directions: np.ndarray, chain_assignment: np.ndarray,
                       rng: np.random.Generator, amplitude_error_db: float,
                       phase_error_deg: float, calibration_phase_deg: float,
                       phase_bits: int = 5) -> np.ndarray:
        """Return F_RF [F, C] with exactly feeds_per_chain nonzeros per active chain.

        ``directions[c]`` is the unit direction used to steer physical chain ``c``.
        ``chain_assignment`` is retained only for API compatibility; it must not
        index into the chain-direction array because that array is already
        indexed by physical chain.  Phase quantisation and calibration errors are
        applied to every feed.
        """
        nf, nc = self.fm.n_feeds, self.fm.n_chains
        directions = np.asarray(directions, dtype=np.float64)
        if directions.shape != (nc, 3):
            raise ValueError(f"directions must have shape {(nc, 3)}, got {directions.shape}")
        w = np.zeros((nf, nc), dtype=np.complex64)
        chain_gain = 10 ** (self.chain_gain_db / 20.0)
        phase_cal = np.deg2rad(calibration_phase_deg)
        phase_err = np.deg2rad(phase_error_deg)
        for c in range(nc):
            if not self.chain_enabled[c]:
                continue
            feeds = np.flatnonzero(self.fm.feed_chain == c)
            if feeds.size != self.cfg.feeds_per_chain:
                continue
            u = directions[c]
            k = 2.0 * np.pi / self.fm.wavelength_m
            geom = k * (self.fm.feed_positions[feeds, 1] * u[1] + self.fm.feed_positions[feeds, 2] * u[2])
            phi = -geom
            phi = quantize_phase(phi, phase_bits)
            amp_db = rng.normal(0.0, amplitude_error_db, size=feeds.size) if amplitude_error_db > 0 else 0.0
            phi = phi + np.deg2rad(self.chain_phase_deg[c]) + phase_cal
            if phase_error_deg > 0:
                phi = phi + rng.normal(0.0, phase_err, size=feeds.size)
            amp = chain_gain[c] * 10 ** (amp_db / 20.0) / np.sqrt(feeds.size)
            w[feeds, c] = (amp * np.exp(1j * phi)).astype(np.complex64)
        return w

    # ---- telemetry -------------------------------------------------------
    def telemetry(self) -> dict[str, Any]:
        # Real telemetry is noisy and quantised.  A detector calibrated on
        # perfectly repeatable values would report artificially perfect scores.
        rng = self._telemetry_rng
        self._telemetry_drift = (0.98 * self._telemetry_drift +
                                 rng.normal(0.0, 1.0, self._telemetry_drift.shape) *
                                 self._telemetry_drift_scale)
        drift = self._telemetry_drift
        per_tile = []
        for t in range(self.cfg.n_tiles):
            ch = np.flatnonzero(self.fm.chain_tile == t)
            per_tile.append({
                "tile": t,
                "enabled": bool(self.tile_enabled[t]),
                "isolated": bool(self.tile_isolated[t]),
                "active_chains": int(np.sum(self.chain_enabled[ch])),
                "gain_db_mean": round(float(np.mean(self.chain_gain_db[ch]) + drift[t, 0] +
                                             rng.normal(0, 0.05)), 3),
                "gain_db_std": round(max(0.0, float(np.std(self.chain_gain_db[ch]) + drift[t, 1] +
                                                    rng.normal(0, 0.03))), 3),
                "phase_error_deg_rms": round(max(0.0, float(np.sqrt(np.mean(self.chain_phase_deg[ch] ** 2))
                                                           + drift[t, 2] + rng.normal(0, 0.12))), 3),
                "vswr_max": round(max(1.0, float(np.max(self.chain_vswr[ch]) + drift[t, 3] +
                                                 rng.normal(0, 0.005))), 3),
                "temp_c": round(float(self.tile_temp_c[t] + drift[t, 4] + rng.normal(0, 0.05)), 3),
                "supply_v": round(float(self.tile_supply_v[t] + drift[t, 5] + rng.normal(0, 0.01)), 3),
                "ptp_offset_ns": round(float(self.tile_ptp_offset_ns[t] + drift[t, 6] +
                                             rng.normal(0, 0.2)), 3),
                "noise_fig_db_max": round(max(0.0, float(np.max(self.chain_noise_fig_db[ch]) + drift[t, 7] +
                                                        rng.normal(0, 0.05))), 3),
                "fan_fail": int(not self.fan_ok),
            })
        rb = {
            "tile_mask": self.tile_enabled.tolist(),
            "chain_mask": self.chain_enabled.tolist(),
            "active_chains": self.active_chains(),
            "state": self.mask_to_state_name(),
            "calibration_epoch": self.calibration_epoch,
            "per_tile": per_tile,
        }
        self.last_readback = rb
        return rb

    def readback(self, resource: str) -> Any:
        rb = self.telemetry()
        if resource == "rf_chain_mask":
            return rb["chain_mask"]
        if resource == "health":
            return rb["per_tile"]
        if resource == "energy_state":
            return rb["state"]
        return rb.get(resource, rb)

    def resync_ptp(self, tile: int) -> None:
        self.tile_ptp_offset_ns[tile] = 0.0
        ch = np.flatnonzero(self.fm.chain_tile == tile)
        self.chain_phase_deg[ch] = 0.0

    def recalibrate(self, rng: np.random.Generator, residual_deg: float) -> None:
        self.chain_phase_deg[:] = rng.normal(0.0, residual_deg, size=self.fm.n_chains)
        self.chain_gain_db[:] = rng.normal(0.0, 0.15, size=self.fm.n_chains)
        self.calibration_epoch += 1
        self.tile_ptp_offset_ns[:] = 0.0
