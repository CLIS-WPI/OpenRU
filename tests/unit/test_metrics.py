import numpy as np

from openru_x6.metrics import (MetricsStore, bootstrap_ci, jain_fairness,
                               paired_delta_ci, percentile)


def test_bootstrap_ci_contains_mean_and_is_ordered():
    x = np.linspace(1.0, 2.0, 100)
    mean, lo, hi = bootstrap_ci(x, n_boot=1000, rng=np.random.default_rng(1))
    assert lo <= mean <= hi
    assert abs(mean - 1.5) < 1e-9


def test_paired_delta_ci_positive_when_a_beats_b():
    a = np.array([10.0, 11.0, 12.0, 13.0])
    b = np.array([8.0, 8.5, 9.0, 9.5])
    out = paired_delta_ci(a, b, n_boot=500)
    assert out["n"] == 4
    assert out["mean_delta"] > 2.0
    assert out["ci_low"] > 0


def test_jain_fairness_extremes():
    assert jain_fairness([1.0, 1.0, 1.0, 1.0]) == 1.0
    assert jain_fairness([0.0, 0.0, 0.0, 1.0]) == 0.25
    assert jain_fairness([]) == 0.0


def test_percentile_and_store_roundtrip(tmp_path):
    store = MetricsStore()
    for i, v in enumerate([1.0, 2.0, 3.0]):
        store.add("X", "s", i, "p", "m", v, "u", "SIMULATED", "digest")
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0
    csv, _ = store.save(tmp_path)
    assert csv.exists()
    assert len(store.rows) == 3
