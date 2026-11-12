"""Optional polarimetric channel abstraction.

The baseline channel uses one scalar response per feed.  This module adds an
optional 2x2 complex Jones matrix per path and user for experiments that need
cross-polar discrimination (XPD), cross-polar ratio (XPR), orientation mismatch
and calibration errors.  It is a behavioural model, not measured antenna data.
"""
from __future__ import annotations

import numpy as np

from .config import PolarizationConfig


def _column_amplitudes(xpd_db: float, xpr_db: float) -> tuple[float, float, float, float]:
    """Return unit-column co/cross amplitudes for the two transmit polarizations."""
    ex = 10 ** (-float(xpd_db) / 10.0)
    ep = 10 ** (-float(xpr_db) / 10.0)
    co_v = np.sqrt(1.0 / (1.0 + ex))
    cross_v = np.sqrt(ex / (1.0 + ex))
    co_h = np.sqrt(1.0 / (1.0 + ep))
    cross_h = np.sqrt(ep / (1.0 + ep))
    return co_v, cross_v, co_h, cross_h


def jones_matrices(cfg: PolarizationConfig, n_users: int, n_paths: int,
                   n_rx: int, rng: np.random.Generator) -> np.ndarray:
    """Draw ``[U,L,Rx,2]`` complex Jones matrices for V/H transmit feeds.

    Each transmit column has unit mean power before calibration/orientation
    perturbations.  The first two receive rows are V/H; extra receive rows (if
    configured) reuse the co-pol response with independent receive phase.
    """
    U, L = int(n_users), int(n_paths)
    co_v, cross_v, co_h, cross_h = _column_amplitudes(cfg.xpd_db, cfg.xpr_db)
    corr = float(np.clip(cfg.correlation, 0.0, 1.0))
    phase = rng.uniform(0.0, 2.0 * np.pi, (U, L, 4))
    # Correlation is applied to the cross-pol phase relative to the co-pol
    # phase.  Corr=1 gives a fully correlated (deterministic) polarization
    # coupling; corr=0 gives independent fast fading on the cross terms.
    phase[..., 1] = corr * phase[..., 0] + np.sqrt(max(1.0 - corr ** 2, 0.0)) * phase[..., 1]
    phase[..., 2] = corr * phase[..., 3] + np.sqrt(max(1.0 - corr ** 2, 0.0)) * phase[..., 2]
    J2 = np.empty((U, L, 2, 2), dtype=np.complex128)
    J2[..., 0, 0] = co_v * np.exp(1j * phase[..., 0])
    J2[..., 1, 0] = cross_v * np.exp(1j * phase[..., 1])
    J2[..., 0, 1] = cross_h * np.exp(1j * phase[..., 2])
    J2[..., 1, 1] = co_h * np.exp(1j * phase[..., 3])
    # Orientation mismatch rotates the polarization basis.
    if cfg.orientation_std_deg > 0:
        theta = np.deg2rad(rng.normal(0.0, cfg.orientation_std_deg, (U, L)))
        c, s = np.cos(theta), np.sin(theta)
        R = np.stack([np.stack([c, -s], axis=-1),
                      np.stack([s, c], axis=-1)], axis=-2)
        J2 = np.einsum("ulij,uljk->ulik", R, J2)
    # Per-pol calibration amplitude/phase errors at the transmitter.
    if cfg.calibration_amplitude_error_db > 0 or cfg.calibration_phase_error_deg > 0:
        amp = 10 ** (rng.normal(0.0, cfg.calibration_amplitude_error_db, (U, L, 2)) / 20.0)
        ph = np.deg2rad(rng.normal(0.0, cfg.calibration_phase_error_deg, (U, L, 2)))
        J2 = J2 * amp[..., None, :] * np.exp(1j * ph)[..., None, :]
    if n_rx <= 2:
        return J2[:, :, :max(n_rx, 1), :]
    # Keep the model usable for larger receive arrays without claiming a
    # calibrated multi-pol receiver: repeat the dual-pol rows with phase.
    extra = n_rx - 2
    tail = J2[:, :, :1, :].repeat(extra, axis=2) * np.exp(
        1j * rng.uniform(0.0, 2.0 * np.pi, (U, L, extra, 1)))
    return np.concatenate([J2, tail], axis=2)
