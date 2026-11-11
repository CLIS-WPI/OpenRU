"""Link adaptation, BLER abstraction and Sionna PHY validation hooks.

The production path uses a calibrated logistic BLER abstraction (SIMULATED).
E00 additionally executes a real Sionna PHY LDPC/QAM link (PHY_VALIDATED) and
compares the waterfall region with the abstraction so that the abstraction is
not silently treated as measured 5G performance.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .config import MimoConfig

# (spectral efficiency bits/s/Hz, SNR threshold dB at BLER=0.1)
MCS_TABLE: list[tuple[float, float]] = [
    (0.234, -6.0), (0.306, -4.5), (0.377, -3.0), (0.490, -1.5), (0.601, 0.0),
    (0.740, 1.5), (0.877, 3.0), (1.170, 4.8), (1.480, 6.3), (1.910, 7.8),
    (2.400, 9.3), (2.730, 10.8), (3.320, 12.3), (3.900, 13.8), (4.500, 15.3),
    (5.100, 16.8), (5.550, 18.3), (6.200, 19.8), (6.600, 21.3), (7.000, 23.0),
    (7.400, 25.0),
]
OVERHEAD = 0.88


def bler_curve(sinr_db: np.ndarray, mcs_index: np.ndarray, slope_db: float = 0.7) -> np.ndarray:
    sinr_db = np.asarray(sinr_db, dtype=float)
    mcs = np.asarray(mcs_index, dtype=int)
    thr = np.array([MCS_TABLE[min(int(m), len(MCS_TABLE) - 1)][1] for m in mcs.ravel()]).reshape(mcs.shape)
    shift = slope_db * np.log(9.0)  # BLER=0.1 at the tabulated threshold
    return 1.0 / (1.0 + np.exp((sinr_db - thr - shift) / slope_db))


def resource_multiplier(resource: dict[str, Any] | None) -> float:
    """Fraction of time-frequency resources available to user-plane data.

    This is deliberately explicit: TDD DL duty cycle, DL symbols, control, DMRS
    and SSB overhead are applied once, and the PRB share is taken from the
    configured bandwidth.  ``capacity_bound`` mode returns 1.0 so a spectral-
    efficiency upper bound can be reported separately from delivered goodput.
    """
    if not resource or resource.get("mode", "nr_grid") == "capacity_bound":
        return 1.0
    symbols = max(int(resource.get("symbols_per_slot", 14)), 1)
    dl_symbols = min(max(int(resource.get("dl_symbols_per_slot", 11)), 1), symbols)
    tdd = float(resource.get("tdd_dl_fraction", 1.0))
    control = float(resource.get("control_overhead_fraction", 0.0))
    dmrs = float(resource.get("dmrs_overhead_fraction", 0.0))
    ssb = float(resource.get("ssb_overhead_fraction", 0.0))
    n_prb = max(int(resource.get("n_prb", 273)), 1)
    n_rb_total = max(int(resource.get("n_rb_total", 273)), 1)
    return float(np.clip(tdd * (dl_symbols / symbols) * (n_prb / n_rb_total) *
                         (1.0 - control) * (1.0 - dmrs) * (1.0 - ssb), 0.0, 1.0))


def link_adaptation(sinr_db: np.ndarray, bandwidth_hz: float, cfg: MimoConfig,
                    phy: Any | None = None,
                    resource: dict[str, Any] | None = None) -> dict[str, np.ndarray]:
    sinr_db = np.atleast_1d(np.asarray(sinr_db, dtype=float))
    K = sinr_db.size
    se = np.zeros(K)
    mcs = np.zeros(K, dtype=int)
    bler = np.ones(K)
    rate = np.zeros(K)
    capacity = np.zeros(K)
    factor = resource_multiplier(resource)
    for k in range(K):
        chosen = 0
        for m, (se_m, thr) in enumerate(MCS_TABLE):
            b = float(bler_curve(np.array([sinr_db[k]]), np.array([m]))[0])
            if b <= cfg.bler_target:
                chosen = m
            else:
                break
        b0 = float(bler_curve(np.array([sinr_db[k]]), np.array([chosen]))[0])
        residual = b0 ** (cfg.max_harq_retx + 1)
        expected_retx = sum(b0 ** r for r in range(1, cfg.max_harq_retx + 1))
        goodput_factor = (1.0 - residual) / (1.0 + expected_retx)
        se[k] = MCS_TABLE[chosen][0] * OVERHEAD
        capacity[k] = se[k] * bandwidth_hz
        mcs[k] = chosen
        bler[k] = b0
        rate[k] = capacity[k] * factor * goodput_factor
    return {"se": se, "mcs": mcs, "bler": bler, "rate_bps": rate,
            "capacity_bps": capacity, "resource_multiplier": factor, "goodput_factor":
            (1.0 - bler ** (cfg.max_harq_retx + 1)) / (1.0 + sum(bler ** r for r in range(1, cfg.max_harq_retx + 1)))}


def sionna_phy_validation(snr_db: list[float] | None = None, batch: int = 64,
                          k: int = 512, n: int = 1024, bits: int = 4, seed: int = 1234) -> dict[str, Any]:
    """Real Sionna PHY coded-link experiment (LDPC + QAM + AWGN)."""
    import torch
    import sionna.phy as phy
    from sionna.phy import config

    snr_db = snr_db or [0.0, 2.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
    dev = config.device
    enc = phy.fec.LDPC5GEncoder(k, n, num_bits_per_symbol=bits)
    dec = phy.fec.LDPC5GDecoder(enc, hard_out=True)
    mapper = phy.mapping.Mapper("qam", bits)
    demapper = phy.mapping.Demapper("app", "qam", bits)
    awgn = phy.channel.AWGN()
    torch.manual_seed(seed)
    b = torch.randint(0, 2, (batch, k), device=dev, dtype=torch.int32)
    c = enc(b)
    x = mapper(c)
    rows = []
    for snr in snr_db:
        no = 10 ** (-snr / 10.0)
        y = awgn(x, no)
        llr = demapper(y, no)
        bh = dec(llr)
        err = (bh != b)
        rows.append({"snr_db": float(snr), "ber": float(err.float().mean()),
                     "bler": float(err.any(dim=1).float().mean())})
    # abstraction comparison at the same spectral efficiency
    se = k / n * bits
    target = min(MCS_TABLE, key=lambda t: abs(t[0] - se))
    for r in rows:
        r["abstraction_bler_at_same_se"] = float(
            bler_curve(np.array([r["snr_db"]]), np.array([MCS_TABLE.index(target)]))[0])
    return {
        "engine": "sionna.phy",
        "sionna_version": getattr(__import__("sionna"), "__version__", "unknown"),
        "k": k, "n": n, "bits_per_symbol": bits, "code_rate": k / n,
        "spectral_efficiency": se, "batch": batch, "seed": seed,
        "rows": rows,
        "evidence_class": "PHY_VALIDATED",
        "note": "AWGN coded-link validation only; does not validate RF hardware or 5G NR conformance.",
    }
