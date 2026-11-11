import numpy as np

from openru_x6.experiments.common import make_context
from openru_x6.scheduler import Scheduler, channel_quality


def test_context_and_scheduler_produce_valid_selection(radio):
    ctx = make_context(radio, seed=3, n_users=24, n_slots=2, saturate=True)
    snap = ctx.snapshot(0)
    backlog = np.full(24, 1e6)
    age = np.zeros(24)
    sched = Scheduler("pf", max_users=min(radio.mimo.max_layers, 16))
    users = sched.select(backlog, channel_quality(snap.H), age)
    assert users.size <= sched.max_users
    assert len(set(users.tolist())) == users.size
    assert np.all((users >= 0) & (users < 24))
