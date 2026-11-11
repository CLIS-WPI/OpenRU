"""Multi-user traffic generation with paired traces and deadline-aware QoS."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TrafficTrace:
    arrivals_bits: np.ndarray      # [S,U]
    deadline_slots: np.ndarray     # [U]
    mean_mbps: float
    load_fraction: float
    slot_duration_s: float

    def replay(self) -> "TrafficQueue":
        return TrafficQueue(self)


class TrafficQueue:
    """FIFO per-user queue with explicit deadline-cohort accounting.

    ``expired_bits`` counts bits that were still queued when their deadline
    passed.  Those bits are not counted again if they are served late, so the
    QoS numerator is the union of expired and overflow-dropped bits.  The
    conservation identity ``arrived = served + dropped + queued`` holds
    independently of deadline expiry.

    Latency percentiles are weighted completion delays for bits that were
    actually served, including late service.  Expired, dropped and
    end-of-run queued bits are reported as censoring/deadline-miss fractions
    and are never inserted as completion samples.
    """

    def __init__(self, trace: TrafficTrace, max_bits_per_user: float = 2e7) -> None:
        self.trace = trace
        self.backlog = np.zeros(trace.arrivals_bits.shape[1])
        self.age = np.zeros_like(self.backlog)
        self.served_bits = np.zeros_like(self.backlog)
        self.late_served_bits = 0.0
        self.expired_bits = 0.0
        self.dropped_bits = 0.0
        self.dropped_expired_bits = 0.0
        self.arrived_bits = 0.0
        self.max_bits = max_bits_per_user
        self.slot = 0
        self._cohorts: list[list[list[float]]] = [[] for _ in range(self.n_users)]
        self._delay_samples: list[tuple[float, float]] = []

    @property
    def n_users(self) -> int:
        return self.backlog.size

    def has_data(self) -> np.ndarray:
        return self.backlog > 0

    def _deadline_slot(self, user: int) -> int:
        return self.slot + int(self.trace.deadline_slots[user])

    def _recompute_backlog(self) -> None:
        self.backlog[:] = [sum(c[2] for c in cohorts) for cohorts in self._cohorts]

    def _recompute_age(self) -> None:
        for u, cohorts in enumerate(self._cohorts):
            self.age[u] = max(0.0, float(self.slot - cohorts[0][0])) if cohorts else 0.0

    def _drop_newest(self, user: int, excess: float) -> float:
        """Drop newest bits first, returning the number of dropped bits."""
        dropped = 0.0
        cohorts = self._cohorts[user]
        while excess > 0 and cohorts:
            c = cohorts[-1]
            take = min(c[2], excess)
            c[2] -= take
            excess -= take
            dropped += take
            # Track overlap so expired bits dropped later are not double-counted.
            self.dropped_expired_bits += min(take, c[3])
            if c[2] <= 1e-12:
                cohorts.pop()
        return dropped

    def _expire_due(self) -> None:
        for cohorts in self._cohorts:
            for c in cohorts:
                if self.slot > c[1] and c[2] > c[3]:
                    newly = c[2] - c[3]
                    c[3] = c[2]
                    self.expired_bits += newly

    def step_arrivals(self) -> None:
        a = self.trace.arrivals_bits[self.slot]
        self.arrived_bits += float(a.sum())
        for u, bits in enumerate(a):
            if bits > 0:
                self._cohorts[u].append([float(self.slot), float(self._deadline_slot(u)),
                                         float(bits), 0.0])
        self.backlog += a
        for u in range(self.n_users):
            over = self.backlog[u] - self.max_bits
            if over > 0:
                self.dropped_bits += self._drop_newest(u, over)
                self.backlog[u] = min(self.backlog[u], self.max_bits)
        self._recompute_backlog()
        self._recompute_age()

    def serve(self, per_user_bits: np.ndarray) -> np.ndarray:
        self._expire_due()
        before = self.backlog.copy()
        alloc = np.maximum(np.asarray(per_user_bits, dtype=float), 0.0)
        served = np.zeros(self.n_users)
        for u in range(self.n_users):
            remaining = min(alloc[u], before[u])
            if remaining <= 0:
                continue
            cohorts = self._cohorts[u]
            while remaining > 0 and cohorts:
                c = cohorts[0]
                take = min(c[2], remaining)
                if take <= 0:
                    cohorts.pop(0)
                    continue
                c[2] -= take
                remaining -= take
                served[u] += take
                completion_delay = float(self.slot - c[0])
                self._delay_samples.append((completion_delay, take))
                if self.slot > c[1]:
                    self.late_served_bits += take
                if c[2] <= 1e-12:
                    cohorts.pop(0)
            self.backlog[u] -= served[u]
        self.served_bits += served
        self._recompute_backlog()
        self._recompute_age()
        self.slot += 1
        return served

    def qos_violation_fraction(self) -> float:
        total = max(self.arrived_bits, 1.0)
        violated = self.expired_bits + self.dropped_bits - self.dropped_expired_bits
        return float(max(violated, 0.0) / total)

    def expired_fraction(self) -> float:
        return float(self.expired_bits / max(self.arrived_bits, 1.0))

    def deadline_miss_fraction(self) -> float:
        return self.expired_fraction()

    def completed_fraction(self) -> float:
        return float(self.served_bits.sum() / max(self.arrived_bits, 1.0))

    def dropped_fraction(self) -> float:
        return float(self.dropped_bits / max(self.arrived_bits, 1.0))

    def queued_fraction(self) -> float:
        return float(self.backlog.sum() / max(self.arrived_bits, 1.0))

    def conservation_error(self) -> float:
        return float(self.arrived_bits - self.served_bits.sum() -
                     self.dropped_bits - self.backlog.sum())

    def mean_delay_slots(self) -> float:
        return float(self.age.mean())

    def latency_percentile(self, q: float) -> float:
        if not self._delay_samples:
            return float("nan")
        samples = np.asarray(self._delay_samples, dtype=float)
        order = np.argsort(samples[:, 0])
        waits = samples[order, 0]
        weights = samples[order, 1]
        cumulative = np.cumsum(weights)
        target = float(q) * cumulative[-1]
        return float(waits[np.searchsorted(cumulative, target, side="left")])


def generate_trace(n_users: int, n_slots: int, slot_duration_s: float, mean_mbps: float,
                   load_fraction: float, burstiness: float, deadline_slots: int,
                   rng: np.random.Generator) -> TrafficTrace:
    """Poisson / gamma bursty arrivals.  Identical trace is replayed by all policies."""
    mean_bits_per_slot = mean_mbps * 1e6 * slot_duration_s * load_fraction
    if burstiness <= 1.01:
        arr = rng.poisson(max(mean_bits_per_slot, 0.0), size=(n_slots, n_users)).astype(float)
    else:
        shape = 1.0 / burstiness
        scale = mean_bits_per_slot * burstiness
        arr = rng.gamma(shape, scale, size=(n_slots, n_users))
        # on/off burstiness: zero out a fraction of slots inversely to load
        if load_fraction < 1.0:
            mask = rng.random((n_slots, n_users)) < max(load_fraction, 0.02)
            arr = arr * mask / max(load_fraction, 0.02)
    deadline = np.full(n_users, deadline_slots, dtype=int)
    return TrafficTrace(arrivals_bits=arr, deadline_slots=deadline, mean_mbps=mean_mbps,
                        load_fraction=load_fraction, slot_duration_s=slot_duration_s)
