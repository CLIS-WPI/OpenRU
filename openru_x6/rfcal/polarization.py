"""Jones-vector polarization model for the OpenRU-X6 dual-polarized array.

The model represents each radiating site as a pair of V/H receive ports.  A
site Jones matrix maps an incident field Jones vector to the two port outputs.
Cross-polarization leakage is configured as a complex ratio relative to the
co-polar response.  The default leakage values are assumptions, not hardware
measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .beamforming import array_response, steering_weights
from .topology import Topology

_FLOOR_DB = -300.0


@dataclass(frozen=True)
class PolarizationConfig:
    """Assumed dual-polarized site response.

    ``cross_pol_db`` is the ratio of the cross-polar port response to the
    co-polar port response.  ``cross_pol_phase_deg`` is the relative phase of
    that leakage.  ``site_phase_step_deg`` adds a deterministic site-to-site
    phase progression to the leakage term.
    """

    cross_pol_db: float = 25.0
    cross_pol_phase_deg: float = 90.0
    site_phase_step_deg: float = 0.0
    name: str = "assumed-cross-pol-25db"
    source: str = "engineering assumption; not a measured polarization isolation"

    def validate(self) -> None:
        if not np.isfinite(self.cross_pol_db) or self.cross_pol_db <= 0.0:
            raise ValueError("cross_pol_db must be finite and positive")
        if not np.isfinite(self.cross_pol_phase_deg):
            raise ValueError("cross_pol_phase_deg must be finite")
        if not np.isfinite(self.site_phase_step_deg):
            raise ValueError("site_phase_step_deg must be finite")

    @property
    def cross_pol_amplitude(self) -> float:
        return float(10.0 ** (-self.cross_pol_db / 20.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cross_pol_db": self.cross_pol_db,
            "cross_pol_phase_deg": self.cross_pol_phase_deg,
            "site_phase_step_deg": self.site_phase_step_deg,
            "name": self.name,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PolarizationConfig":
        data = data or {}
        config = cls(
            cross_pol_db=float(data.get("cross_pol_db", 25.0)),
            cross_pol_phase_deg=float(data.get("cross_pol_phase_deg", 90.0)),
            site_phase_step_deg=float(data.get("site_phase_step_deg", 0.0)),
            name=str(data.get("name", "assumed-cross-pol-25db")),
            source=str(
                data.get(
                    "source",
                    "engineering assumption; not a measured polarization isolation",
                )
            ),
        )
        config.validate()
        return config


def linear_jones(angle_deg: float, phase_deg: float = 0.0) -> np.ndarray:
    """Return a unit linear Jones vector in the V/H basis.

    ``angle_deg`` is measured from V toward H.  The H component may carry a
    relative phase, which permits elliptical polarization.
    """

    angle_rad = np.deg2rad(float(angle_deg))
    phase_rad = np.deg2rad(float(phase_deg))
    vector = np.asarray(
        [np.cos(angle_rad), np.sin(angle_rad) * np.exp(1j * phase_rad)],
        dtype=np.complex128,
    )
    return _normalize_jones(vector)


def circular_jones(handedness: str = "rhcp") -> np.ndarray:
    """Return a unit circular Jones vector using a V/H basis."""

    normalized = handedness.strip().lower()
    if normalized in {"rhcp", "right", "right-hand", "right_hand"}:
        return _normalize_jones(np.asarray([1.0, -1.0j], dtype=np.complex128))
    if normalized in {"lhcp", "left", "left-hand", "left_hand"}:
        return _normalize_jones(np.asarray([1.0, 1.0j], dtype=np.complex128))
    raise ValueError(f"unsupported circular handedness: {handedness!r}")


def orthogonal_jones(jones: np.ndarray) -> np.ndarray:
    """Return the unit Jones vector orthogonal to ``jones``."""

    vector = _as_jones(jones)
    orthogonal = np.asarray([-np.conj(vector[1]), np.conj(vector[0])], dtype=np.complex128)
    return _normalize_jones(orthogonal)


def matched_receiver_jones(incident: np.ndarray) -> np.ndarray:
    """Return the receiver port vector that is matched to ``incident``."""

    vector = _as_jones(incident)
    return _normalize_jones(np.conj(vector))


def site_jones(topology: Topology, config: PolarizationConfig | None = None) -> np.ndarray:
    """Return one 2x2 Jones matrix per site, ordered ``[V, H]``."""

    config = config or PolarizationConfig()
    config.validate()
    leakage = config.cross_pol_amplitude * np.exp(
        1j
        * np.deg2rad(
            config.cross_pol_phase_deg
            + config.site_phase_step_deg * np.arange(topology.n_sites, dtype=float)
        )
    )
    matrices = np.zeros((topology.n_sites, 2, 2), dtype=np.complex128)
    for site in topology.sites:
        matrices[site.index] = np.asarray(
            [[1.0, leakage[site.index]], [leakage[site.index], 1.0]],
            dtype=np.complex128,
        )
    return matrices


def feed_jones(topology: Topology, config: PolarizationConfig | None = None) -> np.ndarray:
    """Return one Jones row vector per feed for the V/H receive ports."""

    matrices = site_jones(topology, config)
    rows = np.zeros((topology.n_feeds, 2), dtype=np.complex128)
    for feed in topology.feeds:
        if feed.polarization == "V":
            row = 0
        elif feed.polarization == "H":
            row = 1
        else:
            raise ValueError(
                f"unsupported polarization {feed.polarization!r} on feed {feed.index}"
            )
        rows[feed.index] = matrices[feed.site, row, :]
    return rows


def receiver_port_weights(
    topology: Topology, receiver_jones: np.ndarray
) -> np.ndarray:
    """Map a receiver Jones vector to one complex port weight per feed."""

    receiver = _as_jones(receiver_jones)
    weights = np.zeros(topology.n_feeds, dtype=np.complex128)
    for feed in topology.feeds:
        if feed.polarization == "V":
            weights[feed.index] = receiver[0]
        elif feed.polarization == "H":
            weights[feed.index] = receiver[1]
        else:
            raise ValueError(
                f"unsupported polarization {feed.polarization!r} on feed {feed.index}"
            )
    return weights


def polarized_steering_weights(
    topology: Topology,
    az_deg: float,
    el_deg: float,
    receiver_jones: np.ndarray,
    *,
    amplitude: np.ndarray | None = None,
) -> np.ndarray:
    """Return geometry steering weights projected onto a receiver polarization."""

    weights = steering_weights(topology, az_deg, el_deg, amplitude=amplitude)
    weights = weights * receiver_port_weights(topology, receiver_jones)
    peak = float(np.max(np.abs(weights)))
    if peak > 0:
        weights = weights / peak
    return weights.astype(np.complex128)


def feed_polarization_gain(
    topology: Topology,
    incident_jones: np.ndarray,
    config: PolarizationConfig | None = None,
) -> np.ndarray:
    """Return the complex scalar response of every feed port to an incident field."""

    incident = _as_jones(incident_jones)
    jones = feed_jones(topology, config)
    return jones @ incident


def array_factor_polarized(
    topology: Topology,
    weights: np.ndarray,
    az_deg: float | np.ndarray,
    el_deg: float | np.ndarray,
    incident_jones: np.ndarray,
    *,
    polarization: PolarizationConfig | None = None,
    path_response: np.ndarray | None = None,
    feed_response: np.ndarray | None = None,
) -> np.ndarray:
    """Return the complex array factor including the site Jones response."""

    weights = np.asarray(weights, dtype=np.complex128)
    if weights.shape != (topology.n_feeds,):
        raise ValueError(
            f"weights must have shape ({topology.n_feeds},), got {weights.shape}"
        )
    response = array_response(topology, az_deg, el_deg)
    if path_response is not None:
        path_response = np.asarray(path_response, dtype=np.complex128)
        if path_response.shape != (topology.n_feeds,):
            raise ValueError(
                f"path_response must have shape ({topology.n_feeds},), "
                f"got {path_response.shape}"
            )
        response = response * path_response
    if feed_response is None:
        feed_response = feed_polarization_gain(topology, incident_jones, polarization)
    else:
        feed_response = np.asarray(feed_response, dtype=np.complex128)
        if feed_response.shape != (topology.n_feeds,):
            raise ValueError(
                f"feed_response must have shape ({topology.n_feeds},), "
                f"got {feed_response.shape}"
            )
    return np.sum(weights * response * feed_response, axis=-1)


def array_gain_polarized_db(
    topology: Topology,
    weights: np.ndarray,
    az_deg: float,
    el_deg: float,
    incident_jones: np.ndarray,
    *,
    polarization: PolarizationConfig | None = None,
    path_response: np.ndarray | None = None,
    feed_response: np.ndarray | None = None,
) -> float:
    """Return coherent gain relative to one unit-amplitude feed."""

    weights = np.asarray(weights, dtype=np.complex128)
    weight_power = float(np.sum(np.abs(weights) ** 2))
    if weight_power <= 0.0:
        return _FLOOR_DB
    factor = array_factor_polarized(
        topology,
        weights,
        az_deg,
        el_deg,
        incident_jones,
        polarization=polarization,
        path_response=path_response,
        feed_response=feed_response,
    )
    gain = float(abs(factor) ** 2 / weight_power)
    if gain <= 0.0:
        return _FLOOR_DB
    return float(10.0 * np.log10(gain))


def _as_jones(value: np.ndarray | tuple[complex, complex]) -> np.ndarray:
    vector = np.asarray(value, dtype=np.complex128)
    if vector.shape != (2,):
        raise ValueError(f"Jones vector must have shape (2,), got {vector.shape}")
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("Jones vector must be finite and non-zero")
    return vector


def _normalize_jones(value: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(value))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("Jones vector must be finite and non-zero")
    return value / norm
