import numpy as np
from hypothesis import given, settings, strategies as st

from openru_x6.engine import mask_for_chains


@given(chains=st.sampled_from([8, 16, 32, 64]))
@settings(max_examples=20, deadline=None)
def test_chains_mask_counts_and_spread(chains):
    mask = mask_for_chains(chains)
    assert mask.dtype == bool
    assert int(mask.sum()) == chains
    per_tile = mask.reshape(16, 4).sum(axis=1)
    assert per_tile.min() == chains // 16
    assert per_tile.max() == (chains + 15) // 16
