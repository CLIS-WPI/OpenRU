"""Abstract eCPRI/O-RAN-like fronthaul impairment model.

This is NOT verified O-RAN 7.2x interoperability.  It models packet sequence,
loss, jitter, latency, compression distortion and synchronization failure so
that failures remain observable instead of being interpolated away.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class FronthaulConfig:
    packets_per_slot: int = 64
    loss_prob: float = 0.0
    jitter_us: float = 5.0
    base_latency_us: float = 100.0
    deadline_us: float = 250.0
    compression_bits: int = 9
    sync_offset_ns: float = 0.0
    sync_lost: bool = False


class FronthaulLink:
    def __init__(self, cfg: FronthaulConfig, rng: np.random.Generator, seed: int) -> None:
        self.cfg = cfg
        self.rng = rng
        self.seed = seed
        self._last_seq = -1
        self.total = 0
        self.lost = 0
        self.late = 0
        self.reordered = 0
        self.seq_errors = 0
        self.sync_slots = 0
        self.slots = 0
        self.evm = self._compression_evm(cfg.compression_bits)

    @staticmethod
    def _compression_evm(bits: int) -> float:
        if bits <= 0:
            return 0.0
        return float(min(0.5, 2.0 * 2.0 ** (-bits)))

    def transmit_slot(self, payload_bits: float) -> dict[str, Any]:
        c = self.cfg
        self.slots += 1
        n = c.packets_per_slot
        seqs = np.arange(self._last_seq + 1, self._last_seq + 1 + n)
        self._last_seq += n
        loss = self.rng.random(n) < c.loss_prob
        delay = c.base_latency_us + np.abs(self.rng.normal(0.0, c.jitter_us, n))
        late = delay > c.deadline_us
        reordered = int(np.sum(np.diff(delay) < 0))
        lost = int(loss.sum())
        late_n = int(late.sum())
        # sequence errors observed at the receiver
        received_seq = seqs[~loss]
        seq_err = 0
        if received_seq.size > 1:
            gaps = np.diff(received_seq)
            seq_err = int(np.sum(gaps != 1))
        self.total += n
        self.lost += lost
        self.late += late_n
        self.reordered += reordered
        self.seq_errors += seq_err
        if c.sync_lost:
            self.sync_slots += 1
        # effective goodput: successfully delivered, on-time packets; sync loss drops half a slot
        usable = (n - lost - late_n) / n
        if c.sync_lost:
            usable *= 0.5
        usable = max(0.0, usable)
        return {
            "packets": n, "lost": lost, "late": late_n, "reordered": reordered,
            "seq_errors": seq_err, "usable_fraction": usable,
            "evm": self.evm, "compression_bits": c.compression_bits,
            "sync_lost": c.sync_lost, "sync_offset_ns": c.sync_offset_ns,
            "payload_bits": payload_bits, "goodput_bits": payload_bits * usable,
            "timing_violation": bool(late_n > 0 or (c.sync_lost)),
        }

    def impair_sinr_db(self, sinr_db: float) -> float:
        sinr = 10 ** (sinr_db / 10.0)
        evm2 = self.evm ** 2 + (0.05 ** 2 if self.cfg.sync_lost else 0.0)
        eff = 1.0 / (1.0 / max(sinr, 1e-12) + evm2)
        loss_frac = self.lost / max(self.total, 1)
        eff *= (1.0 - loss_frac)
        return float(10 * np.log10(max(eff, 1e-30)))

    def summary(self) -> dict[str, Any]:
        return {
            "packets_total": self.total, "loss_rate": self.lost / max(self.total, 1),
            "late_rate": self.late / max(self.total, 1),
            "reorder_rate": self.reordered / max(self.total, 1),
            "sequence_error_rate": self.seq_errors / max(self.total, 1),
            "sync_loss_fraction": self.sync_slots / max(self.slots, 1),
            "compression_evm": self.evm, "compression_bits": self.cfg.compression_bits,
            "evidence_class": "SIMULATED",
        }
