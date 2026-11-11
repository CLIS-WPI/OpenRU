"""Multi-user schedulers: proportional fair, round robin and max throughput."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Scheduler:
    policy: str = "pf"
    max_users: int = 16
    beta: float = 0.98
    avg_rate: np.ndarray = field(default_factory=lambda: np.zeros(0))
    rr_pointer: int = 0
    qos_weight: float = 1.0

    def _ensure(self, n: int) -> None:
        if self.avg_rate.size != n:
            self.avg_rate = np.ones(n)

    def select(self, backlog_bits: np.ndarray, quality: np.ndarray,
               age_slots: np.ndarray | None = None) -> np.ndarray:
        self._ensure(backlog_bits.size)
        eligible = np.flatnonzero(backlog_bits > 0)
        if eligible.size == 0:
            return np.zeros(0, dtype=int)
        K = min(self.max_users, eligible.size)
        q = np.maximum(quality, 1e-30)
        if self.policy == "rr":
            order = np.argsort((np.arange(eligible.size) - self.rr_pointer) % max(eligible.size, 1))
            chosen = eligible[order][:K]
            self.rr_pointer = (self.rr_pointer + K) % max(eligible.size, 1)
        elif self.policy == "mt":
            chosen = eligible[np.argsort(-q[eligible])[:K]]
        else:  # proportional fair
            metric = q[eligible] / np.maximum(self.avg_rate[eligible], 1e-30)
            if age_slots is not None and self.qos_weight > 0:
                urgen = 1.0 + self.qos_weight * np.clip(age_slots[eligible] / 20.0, 0, 2)
                metric = metric * urgen
            chosen = eligible[np.argsort(-metric)[:K]]
        self.avg_rate *= self.beta
        self.avg_rate[chosen] += (1 - self.beta) * q[chosen]
        return chosen

    def update_served(self, users: np.ndarray, rates: np.ndarray) -> None:
        if users.size:
            self.avg_rate[users] = 0.9 * self.avg_rate[users] + 0.1 * rates


def channel_quality(H, users: np.ndarray | None = None) -> np.ndarray:
    """Path-loss + array-energy proxy used for scheduling decisions."""
    import torch
    e = torch.mean(torch.abs(H) ** 2, dim=(1, 2, 3)).detach().cpu().numpy()
    return e
