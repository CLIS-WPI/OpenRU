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

    Accounting domains are intentionally explicit:

    * ``tdd_dl_fraction``: fraction of slots available for DL;
    * ``dl_symbols_per_slot / symbols_per_slot``: data-bearing symbol fraction
      inside a DL slot;
    * ``n_prb / n_rb_total``: fraction of the configured PRB grid allocated;
    * control, DMRS and SSB: mutually exclusive overhead fractions in the
      allocated DL symbols.

    These factors are multiplied once.  ``phy.OVERHEAD`` is a separate coded-link
    efficiency applied in :func:`link_adaptation`; it is not another copy of the
    TDD/control/DMRS/SSB accounting.  ``capacity_bound`` mode returns 1.0 so an
    upper bound can be reported separately from delivered goodput.  A zero PRB,
    zero TDD or zero DL-symbol resource returns exactly zero.
    """
    if not resource or resource.get("mode", "nr_grid") == "capacity_bound":
        return 1.0
    symbols = max(int(resource.get("symbols_per_slot", 14)), 1)
    dl_symbols = int(resource.get("dl_symbols_per_slot", 11))
    tdd = float(resource.get("tdd_dl_fraction", 1.0))
    control = float(resource.get("control_overhead_fraction", 0.0))
    dmrs = float(resource.get("dmrs_overhead_fraction", 0.0))
    ssb = float(resource.get("ssb_overhead_fraction", 0.0))
    n_prb = int(resource.get("n_prb", 273))
    n_rb_total = int(resource.get("n_rb_total", 273))
    if n_prb <= 0 or n_rb_total <= 0 or tdd <= 0.0 or dl_symbols <= 0:
        return 0.0
    dl_symbols = min(dl_symbols, symbols)
    return float(np.clip(tdd * (dl_symbols / symbols) * (n_prb / n_rb_total) *
                         (1.0 - control) * (1.0 - dmrs) * (1.0 - ssb), 0.0, 1.0))


def nr_grid_audit(cell: Any, resource: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a table-ready audit of NR grid and resource-accounting domains."""
    if resource is None:
        resource = {
            "mode": getattr(cell, "resource_mode", "nr_grid"),
            "n_prb": getattr(cell, "n_prb", 273),
            "n_rb_total": getattr(cell, "n_prb", 273),
            "symbols_per_slot": getattr(cell, "symbols_per_slot", 14),
            "dl_symbols_per_slot": getattr(cell, "dl_symbols_per_slot", 11),
            "tdd_dl_fraction": getattr(cell, "tdd_dl_fraction", 0.75),
            "control_overhead_fraction": getattr(cell, "control_overhead_fraction", 0.08),
            "dmrs_overhead_fraction": getattr(cell, "dmrs_overhead_fraction", 0.083),
            "ssb_overhead_fraction": getattr(cell, "ssb_overhead_fraction", 0.01),
        }
    scs = float(getattr(cell, "subcarrier_spacing_hz", 30_000.0))
    n_prb = int(resource.get("n_prb", getattr(cell, "n_prb", 273)))
    n_subcarriers = n_prb * 12
    occupied_bw = n_subcarriers * scs
    nominal_bw = float(getattr(cell, "bandwidth_hz", occupied_bw))
    factor = resource_multiplier(resource)
    return {
        "mode": resource.get("mode", "nr_grid"),
        "n_prb": n_prb,
        "n_rb_total": int(resource.get("n_rb_total", getattr(cell, "n_prb", n_prb))),
        "n_subcarriers_per_prb": 12,
        "occupied_subcarriers": n_subcarriers,
        "occupied_bandwidth_hz": occupied_bw,
        "occupied_bandwidth_mhz": occupied_bw / 1e6,
        "nominal_bandwidth_hz": nominal_bw,
        "nominal_bandwidth_mhz": nominal_bw / 1e6,
        "grid_utilization": occupied_bw / max(nominal_bw, 1e-12),
        "subcarrier_spacing_hz": scs,
        "slot_duration_s": float(getattr(cell, "slot_duration_s", 5e-4)),
        "symbols_per_slot": int(resource.get("symbols_per_slot", 14)),
        "dl_symbols_per_slot": int(resource.get("dl_symbols_per_slot", 11)),
        "tdd_dl_fraction": float(resource.get("tdd_dl_fraction", 1.0)),
        "control_overhead_fraction": float(resource.get("control_overhead_fraction", 0.0)),
        "dmrs_overhead_fraction": float(resource.get("dmrs_overhead_fraction", 0.0)),
        "ssb_overhead_fraction": float(resource.get("ssb_overhead_fraction", 0.0)),
        "resource_multiplier": factor,
        "coded_link_overhead": OVERHEAD,
        "effective_delivered_fraction": factor * OVERHEAD,
        "domains": {
            "tdd": "fraction of slots available for DL",
            "symbols": "data-bearing DL symbols within an available slot",
            "prb": "allocated PRBs relative to the configured grid",
            "control_dmrs_ssb": "mutually exclusive overhead in allocated DL symbols",
            "overhead": "separate coded-link efficiency applied after resource accounting",
        },
        "note": "273 PRB x 12 x 30 kHz = 98.28 MHz occupied; 100 MHz is the nominal carrier envelope.",
    }


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


def _sionna_uses_torch(phy: Any) -> bool:
    """Return true when the concrete Torch Sionna 2.x LDPC class is exposed."""
    return hasattr(getattr(phy, "fec", None), "LDPC5GEncoder")


def sionna_phy_validation(snr_db: list[float] | None = None, batch: int = 64,
                          k: int = 512, n: int = 1024, bits: int = 4, seed: int = 1234) -> dict[str, Any]:
    """Real Sionna PHY coded-link experiment (LDPC + QAM + AWGN).

    Supports both the TensorFlow-backed Sionna 1.x ``sionna.phy`` API available
    in some local environments and the Torch-backed Sionna 2.x layout used by
    the pinned container.  The returned evidence class is PHY_VALIDATED for the
    coded link only; it is not RF or NR-conformance evidence.
    """
    import sionna
    import sionna.phy as phy

    snr_db = snr_db or [0.0, 2.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
    rows: list[dict[str, float]] = []

    # Sionna 1.x exposes the 5G LDPC classes under ``phy.fec.ldpc`` and uses
    # TensorFlow tensors.  Sionna 2.x exposes them at ``phy.fec`` and uses
    # Torch.  Sionna 2.x also keeps an ``fec.ldpc`` namespace, so test for the
    # concrete top-level class rather than the submodule.
    if not _sionna_uses_torch(phy):
        import tensorflow as tf

        enc = phy.fec.ldpc.LDPC5GEncoder(k, n, num_bits_per_symbol=bits)
        dec = phy.fec.ldpc.LDPC5GDecoder(enc, hard_out=True)
        mapper = phy.mapping.Mapper("qam", bits)
        demapper = phy.mapping.Demapper("app", "qam", bits)
        awgn = phy.channel.AWGN()
        tf.random.set_seed(int(seed))
        b = tf.cast(tf.random.uniform((batch, k), minval=0, maxval=2, dtype=tf.int32),
                    tf.float32)
        c = enc(b)
        x = mapper(c)
        for snr in snr_db:
            no = tf.constant(10 ** (-float(snr) / 10.0), dtype=tf.float32)
            y = awgn(x, no)
            llr = demapper(y, no)
            bh = dec(llr)
            err = tf.not_equal(bh, b)
            rows.append({"snr_db": float(snr),
                         "ber": float(tf.reduce_mean(tf.cast(err, tf.float32)).numpy()),
                         "bler": float(tf.reduce_mean(
                             tf.cast(tf.reduce_any(err, axis=1), tf.float32)).numpy())})
        engine = "sionna.phy(tensorflow)"
    else:
        import torch
        from sionna.phy import config

        dev = getattr(config, "device", None) or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu")
        enc = phy.fec.LDPC5GEncoder(k, n, num_bits_per_symbol=bits)
        dec = phy.fec.LDPC5GDecoder(enc, hard_out=True)
        mapper = phy.mapping.Mapper("qam", bits)
        demapper = phy.mapping.Demapper("app", "qam", bits)
        awgn = phy.channel.AWGN()
        torch.manual_seed(int(seed))
        b = torch.randint(0, 2, (batch, k), device=dev, dtype=torch.int32)
        c = enc(b)
        x = mapper(c)
        for snr in snr_db:
            no = 10 ** (-float(snr) / 10.0)
            y = awgn(x, no)
            llr = demapper(y, no)
            bh = dec(llr)
            err = (bh != b)
            rows.append({"snr_db": float(snr), "ber": float(err.float().mean()),
                         "bler": float(err.any(dim=1).float().mean())})
        engine = "sionna.phy(torch)"

    # Abstraction comparison at the same spectral efficiency.  This is just a
    # cross-check: the logistic curve is not a measured 5G link.
    se = k / n * bits
    target = min(MCS_TABLE, key=lambda t: abs(t[0] - se))
    for r in rows:
        r["abstraction_bler_at_same_se"] = float(
            bler_curve(np.array([r["snr_db"]]), np.array([MCS_TABLE.index(target)]))[0])
    return {
        "engine": engine,
        "sionna_version": getattr(sionna, "__version__", "unknown"),
        "k": k, "n": n, "bits_per_symbol": bits, "code_rate": k / n,
        "spectral_efficiency": se, "batch": batch, "seed": seed,
        "rows": rows,
        "evidence_class": "PHY_VALIDATED",
        "note": "AWGN coded-link validation only; does not validate RF hardware or 5G NR conformance.",
    }
