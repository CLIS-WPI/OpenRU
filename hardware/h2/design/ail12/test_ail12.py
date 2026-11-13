"""Self-checks for the A-IL12 analysis code (model consistency, not design acceptance).
Run: python3 -I -m pytest -q -p no:cacheprovider hardware/h2/design/ail12/test_ail12.py"""
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dataclasses import replace

import calc
import run_sim as R
from model import Cfg, Sim
from params import P

TAGS = {'DS', 'DS-MIN', 'DS-MAX', 'DS-TYP', 'DS-MIN/TYP/MAX', 'DS-MIN/MAX', 'DS-TYP/MAX', 'DERIVED', 'FIXTURE',
        'CANDIDATE', 'ASSUMED', 'HYPOTHETICAL'}


def test_registry_tags_and_unbounded_delays_are_typ():
    assert all(q.tag in TAGS for q in P.values())
    for k in ('t_ovlo', 't_sc', 't_swov', 'tpd_mr', 'isc_gain', 'ift'):
        assert P[k].tag == 'DS-TYP', k          # no guaranteed limit exists for these; must never be promoted


def test_calc_runs_and_self_asserts():
    calc.main()
    assert (HERE / 'out' / 'calc.txt').exists()


def test_steady_state_no_false_trip():
    s = Sim(Cfg(t_end=200e-6)).run()
    m, _ = R.metrics(s)
    assert not s.log
    assert 4.9 < m['min_v_out'] <= m['pk_v_out'] < 5.08


def test_corrected_hard_short_disconnects_and_asserts_P():
    s = Sim(R.fault('t_hard', r_short=0.01)).run()
    m, _ = R.metrics(s)
    assert m['pk_v_out'] < 5.5 and 'SRIN' not in m['violations']
    assert m['t_p08_us'] < 10 and m['t_u10_off_us'] < 10


def test_proposal_bss84_never_reaches_0v8_and_violates_slew():
    s = Sim(R.fault('t_prop', r_short=0.01, **R.PROPOSAL)).run()
    m, _ = R.metrics(s)
    assert math.isnan(m['t_p08_us']) and m['v_p_end'] > 0.9
    assert 'SRIN(R)' in m['violations']


def test_sim_peak_below_analytic_bound():
    """Analytic bound (calc section 13) assumes U1 OUT jumps to its peak at t = 0; the sim must not exceed it."""
    T = 3e-6
    cfg = R.fault('t_bound', r_short=0.01, ft_enabled=False, t_ovlo=T, t_aux=T, **R.CMIN)
    m, _d = R.metrics(Sim(cfg).run())
    vpk = m['pk_v_ldo']
    tau = (cfg.r_in + cfg.ron) * (cfg.c_out + cfg.c_in)
    v0 = 5.08
    bound = vpk - (vpk - v0) * math.exp(-(T + 0.2e-6) / tau)   # +0.2 us: OVLO pin crossing after short onset
    assert m['pk_v_out'] <= bound


def test_bss84_equilibrium_matches_level1_calc():
    s = Sim(replace(R.fault('t_b', r_short=0.01, iface='bss84', vth_p=0.9), t_end=R.TF + 300e-6)).run()
    m, _ = R.metrics(s)
    # calc.py: |Vth| 0.9 V, AUXOFF 0 V -> P = 1.28 V with +5V_IL = 5.08 V; sim +5V_IL is ~5.0 V
    assert abs(m['v_p_end'] - 1.27) < 0.1
