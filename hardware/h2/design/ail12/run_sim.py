"""A-IL12 scenario runner (BEHAVIOURAL / PRELIMINARY). Run: python3 -I run_sim.py [--quick]
Writes out/runs.csv, out/sweep_*.csv, out/limits.csv, out/traces/*.csv, out/fig_*.png, out/sim_log.txt, out/summary.json.
All times in the outputs are measured from the start of the U1 short (or of the source event for normal cases)."""
import csv
import json
import math
import os
import pathlib
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import matplotlib
import numpy as np
import scipy

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calc import cap_corners
from model import Cfg, Sim
from params import v

TRAPZ = getattr(np, 'trapezoid', None) or np.trapz

OUT = HERE / 'out'
TF = 50e-6                         # fault instant (after 50 us of steady operation)
CC = cap_corners()
TAIL = v('tail_us')
LIM = {'v_out': (5.5, 6.0), 'v_in': (23.0, 28.0), 'v_en': (5.0, 6.5), 'v_ovlo': (1.5, 6.5), 'v_aux': (5.0, 6.5),
       'v_mr': (5.5, 6.0)}

BASE = Cfg(t_fault=TF, t_end=TF + 2e-3)
CMIN = {'c_out': CC['c_out'][0], 'c2': CC['c2'][0], 'c_in': CC['c_in'][0], 'c5': CC['c5'][0], 'ron': v('ron_max'), 'th': 2}
CMAX = {'c_out': CC['c_out'][2], 'c2': CC['c2'][2], 'c_in': CC['c_in'][2], 'c5': CC['c5'][2]}
PROPOSAL = {'iface': 'bss84', 'r_in': 5e-3, 'c_in': 0.1e-6 * 0.9 * 0.85 * 0.5,
                'c2': 4.7e-6 * 0.9 * 0.85 * v('dcb_4u7_0603_10v', 0), 'r_ilm_note': None}
PROPOSAL.pop('r_ilm_note')
REC = {'th': 2, 'vldo': v('vldo', 0), 'r_ov': (10.0e3 * 1.0035, 2.94e3 * 0.9965)}


def metrics(s: Sim):
    c = s.c
    d = s.series()
    t0 = c.t_fault if c.t_fault < math.inf else 0.0
    a = d['t'] >= t0
    m = {'name': c.name}
    for k in ('v_out', 'v_in', 'v_ldo', 'v_en', 'v_ovlo', 'v_aux', 'v_mr', 'v_vcb'):
        m[f'pk_{k}'] = float(d[k][a].max())
    m['min_v_out'] = float(d['v_out'][a].min())
    tt = np.arange(d['t'][a][0], d['t'][a][-1], 10e-9) if c.t_fault < math.inf else np.arange(0, d['t'][-1], 1e-6)
    tt = tt[:2_000_000]
    vi = np.interp(tt, d['t'], d['v_in'])
    sl = np.diff(vi) / np.diff(tt) if len(tt) > 1 else np.array([0.0])     # slew on a uniform 10 ns grid
    m['sr_in_rise_Vus'] = float(sl.max() / 1e6) if sl.size else 0.0
    m['sr_in_fall_Vus'] = float(-sl.min() / 1e6) if sl.size else 0.0
    pl = np.where(a & (d['v_p'] <= 0.8))[0]
    m['t_p08_us'] = float((d['t'][pl[0]] - t0) * 1e6) if len(pl) else math.nan
    m['v_p_end'] = float(d['v_p'][-1])
    sink = np.where(a & (d['i_ps'] >= 2.0e-3))[0]
    t_ps = d['t'][sink[0]] if len(sink) else math.inf
    t_u3 = s.first('U3 RESET asserted', t0)
    t_sink = min(t_ps, t_u3 if not math.isnan(t_u3) else math.inf)
    m['t_sink_us'] = (t_sink - t0) * 1e6 if t_sink < math.inf else math.nan
    m['t_drain_bound_us'] = m['t_sink_us'] + TAIL if not math.isnan(m['t_sink_us']) else math.nan
    sh = np.where(a & (d['v_shdn'] <= 0.8))[0]
    m['t_shdn08_us'] = float((d['t'][sh[0]] - t0) * 1e6) if len(sh) else math.nan
    m['t_cd_us'] = (s.first('CD fires', t0) - t0) * 1e6
    m['t_u10_off_us'] = (s.first('U10 FET off', t0) - t0) * 1e6
    m['t_u10_uvlo_us'] = (s.first('U10 UVLO (+5V_IL < 3.88', t0) - t0) * 1e6
    m['t_efuse_off_us'] = (min(s.first('eFuse FET off', t0), math.inf) - t0) * 1e6
    m['t_aux_low_us'] = (s.first('AUXOFF pulled low', t0) - t0) * 1e6
    m['t_u3_us'] = (t_u3 - t0) * 1e6
    m['ft_tripped'] = any('fast-trip comparator' in x[1] for x in s.log if x[0] >= t0)
    m['pk_i_fet_A'] = float(d['i_f'][a].max())
    m['pk_p_fet_W'] = float(d['p_fet'][a].max())
    m['e_fet_uJ'] = float(TRAPZ(d['p_fet'][a], d['t'][a]) * 1e6)
    m['pk_i_rin_A'] = float(np.abs(d['i_rin'][a]).max())
    m['e_rin_uJ'] = float(TRAPZ(d['p_rin'][a], d['t'][a]) * 1e6)
    m['pk_i_short_A'] = float(np.abs(d['i_s'][a]).max())
    m['e_short_uJ'] = float(TRAPZ(d['p_s'][a], d['t'][a]) * 1e6)
    m['pk_i_psink_mA'] = float(d['i_ps'][a].max() * 1e3)
    m['pk_p_psink_mW'] = float(d['p_ps'][a].max() * 1e3)
    m['t_u10_enable_ms'] = math.nan
    en = [t for t, x in s.log if 'U10 enable' in x and t > t0]
    if en:
        m['t_u10_enable_ms'] = (en[0] - t0) * 1e3
    viol = []
    for k, (roc, ab) in LIM.items():
        pk = m[f'pk_{k}']
        if pk > ab:
            viol.append(f'{k}>{ab}V(absmax)')
        elif pk > roc:
            viol.append(f'{k}>{roc}V(ROC)')
    if m['sr_in_rise_Vus'] > 100:
        viol.append('SRIN(R)>100V/us')
    if m['sr_in_fall_Vus'] > 10:
        viol.append('SRIN(F)>10V/us')
    if c.t_fault < math.inf and not math.isnan(m['t_drain_bound_us']) and m['t_drain_bound_us'] > 50:
        viol.append('R4(onset=short)>50us')
    m['violations'] = ';'.join(viol)
    return m, d


def run_one(cfg):
    s = Sim(cfg).run()
    m, d = metrics(s)
    m.update({k: (val if not isinstance(val, tuple) else str(val)) for k, val in asdict(cfg).items() if k != 'name'})
    return m, s.log, (d if cfg.name.startswith('TR_') else None)


def fault(name, **kw):
    kw.setdefault('t_end', TF + 2e-3)
    return replace(BASE, name=name, **kw)


def scenarios(quick=False):
    S = []
    V12 = ((0.0, 12.0),)
    # ---- G1 normal operation ----
    S.append(Cfg(name='TR_N1_startup', init='off', vset=((0, 0), (1e-3, 12.0)), t_end=0.25, max_step_slow=50e-6))
    S.append(Cfg(name='TR_N2_shutdown', vset=((0, 12.0), (1e-3, 12.0), (2e-3, 0.0)), t_end=40e-3))
    S.append(Cfg(name='TR_N3_brownout_3V', vset=((0, 12.0), (1e-3, 12.0), (1.1e-3, 3.0), (20e-3, 3.0), (20.1e-3, 12.0)),
                 i_sink=5.0, t_end=0.25, max_step_slow=50e-6))
    S.append(Cfg(name='N4_brownout_5V4', vset=((0, 12.0), (1e-3, 12.0), (1.1e-3, 5.4), (6e-3, 5.4), (6.1e-3, 12.0)),
                 t_end=10e-3))
    S.append(Cfg(name='N5_highline_13V2', t_end=2e-3))
    # ---- G2 fault grid (DS-typ delays, nominal corner) ----
    for rs in (0.01, 0.1, 1.0, 10.0):
        for te in (10e-9, 1e-6, 100e-6, 10e-3):
            if quick and (rs, te) not in ((0.01, 10e-9), (1.0, 100e-6)):
                continue
            S.append(fault(f'G2_rs{rs:g}_edge{te*1e6:g}us', r_short=rs, t_edge=te, t_end=TF + te + 2e-3))
    S.append(fault('TR_G2_hard_nominal', r_short=0.01))
    S.append(fault('G2_hard_12V', r_short=0.01, vset=V12))
    S.append(fault('G2_hard_noL', r_short=0.01, l_cab=1e-9))
    # ---- G3 current-limited bench source ----
    for icc in (0.1, 0.5, 2.0):
        for tcc in (0.0, 100e-6):
            for cs in (10e-6, 470e-6):
                if quick and not (icc == 0.1 and cs == 470e-6):
                    continue
                S.append(fault(f'G3_icc{icc:g}_tcc{tcc*1e6:g}us_csrc{cs*1e6:g}u', r_short=0.01, i_cc=icc, t_cc=tcc,
                               c_src=cs, t_end=TF + 5e-3))
    # ---- G4 corners on the hard short ----
    for cn, ck in (('cmin', CMIN), ('cmax', CMAX)):
        for th in (0, 2):
            S.append(fault(f'G4_{cn}_th{th}', r_short=0.01, **{**ck, 'th': th}))
    S.append(fault('G4_hot_n7002', r_short=0.01, rds_n=v('n7002_rds', 1), vth_n=1.0))
    S.append(fault('G4_ilmax_lowload', r_short=0.01, i_il=v('i_il', 0), **CMAX))
    # ---- G5 P-interface comparison (persistent short) ----
    S.append(fault('TR_G5_corrected', r_short=0.01, t_end=TF + 15e-3))
    S.append(fault('TR_G5_bss84_vth2.0', r_short=0.01, iface='bss84', vth_p=2.0, t_end=TF + 15e-3))
    S.append(fault('G5_bss84_vth0.9', r_short=0.01, iface='bss84', vth_p=0.9, t_end=TF + 15e-3))
    S.append(fault('TR_G5_none_U3only', r_short=0.01, iface='none', t_end=TF + 15e-3, **CMAX, i_il=v('i_il', 0)))
    S.append(fault('G5_corrected_auxol0.7', r_short=0.01, vaux_ol=0.7, vth_n=1.0, t_end=TF + 15e-3))
    # ---- G7 recovery / unintended re-enable (td = min 140 ms) ----
    # nominal corner: OVLO falling threshold (4.80 V) < U1 OUT (5.00 V) -> stays tripped after the short clears
    S.append(fault('G7_clear1ms_corrected_nominal', r_short=0.01, t_clear=1e-3, t_end=TF + 40e-3))
    # recovery corner: VOV(F) max, divider k min, U1 OUT 4.92 V -> falling threshold 4.94 V > U1 OUT: auto-recovers
    for tc in (1e-3, 20e-3):
        for iface in ('corrected', 'bss84'):
            S.append(fault(f'TR_G7_clear{tc*1e3:g}ms_{iface}_reccorner', r_short=0.01, t_clear=tc, iface=iface,
                           t_end=TF + tc + 0.2, max_step_slow=50e-6, **REC))
    S.append(fault('G7_clear1ms_corrected_reccorner_swov0', r_short=0.01, t_clear=1e-3, t_swov=0.0,
                   t_end=TF + 1e-3 + 0.2, max_step_slow=50e-6, **REC))
    # ---- G8 proposal as drawn (no R_in, 10 V C2, BSS84) ----
    S.append(fault('TR_G8_proposal_hard', r_short=0.01, **PROPOSAL))
    S.append(fault('G8_proposal_rs0.1', r_short=0.1, **PROPOSAL))
    S.append(fault('G8_proposal_hard_noFT', r_short=0.01, ft_enabled=False, **PROPOSAL))
    S.append(fault('G8_proposal_hard_cmin_noFT', r_short=0.01, ft_enabled=False, **{**CMIN, **PROPOSAL}))
    # ---- H back-power: hypothetical IN->OUT off-state leakage in OVLO ----
    for il in (0.0, 1e-3, 5e-3, 10e-3):
        S.append(fault(f'H_leak{il*1e3:g}mA', r_short=0.01, i_leak=il, i_il=v('i_il', 0), t_end=TF + 30e-3))
    return S


def sweeps(quick=False):
    """HYPOTHETICAL delay sweeps. Values are NOT datasheet guarantees."""
    S = []
    cases = {'hard_cmin': dict(r_short=0.01, **CMIN), 'hard_nom': {'r_short': 0.01},
             'rs1_edge1us_cmin': dict(r_short=1.0, t_edge=1e-6, **CMIN),
             'proposal_hard_cmin': dict(r_short=0.01, **{**CMIN, **PROPOSAL})}
    grid = (0.5, 1.2, 2, 3, 5, 10, 20, 50) if not quick else (1.2, 5)
    for cn, kw in cases.items():
        for to in grid:
            S.append(('ovlo_noFT', cn, to, fault(f'SW_ovlo_{cn}_{to:g}us', ft_enabled=False, t_ovlo=to * 1e-6,
                                                 t_aux=to * 1e-6, t_end=TF + to * 1e-6 + 300e-6, **kw)))
        for tsc in ((0.5, 2, 5, 20) if not quick else (0.5,)):
            S.append(('ft_ovlo50', cn, tsc, fault(f'SW_ft_{cn}_{tsc:g}us', t_sc=tsc * 1e-6, t_ovlo=50e-6,
                                                  t_aux=50e-6, t_end=TF + 400e-6, **kw)))
    for ta in ((0.0, 1.2, 10, 33, 100, 1000) if not quick else (1.2, 100)):
        S.append(('aux', 'hard_nom', ta, fault(f'SW_aux_{ta:g}us', r_short=0.01, t_aux=ta * 1e-6,
                                               t_end=TF + max(2e-3, ta * 1e-6 + 1e-3))))
    S.append(('aux', 'hard_nom', math.inf, fault('SW_aux_never', r_short=0.01, t_aux=1.0, t_end=TF + 15e-3, **CMAX,
                                                  i_il=v('i_il', 0))))
    return S


def bisect_limit(args):
    cn, kw, lim = args
    lo, hi = 0.05e-6, 200e-6
    pk = lambda to: metrics(Sim(fault(f'BI_{cn}', ft_enabled=False, t_ovlo=to, t_aux=to, t_end=TF + to + 200e-6,
                                      **kw)).run())[0]['pk_v_out']
    if pk(hi) <= lim:
        return cn, lim, math.inf
    if pk(lo) > lim:
        return cn, lim, 0.0
    for _ in range(14):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if pk(mid) <= lim else (lo, mid)
    return cn, lim, lo * 1e6


def _sweep_one(item):
    kind, cn, x, cfg = item
    m, _, _ = run_one(cfg)
    return dict(kind=kind, case=cn, x_us=x, **{k: m[k] for k in ('pk_v_out', 't_p08_us', 't_sink_us', 't_drain_bound_us',
                                                                   't_shdn08_us', 'pk_i_fet_A', 'e_fet_uJ', 'ft_tripped',
                                                                   'violations')})


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f'{x:.6g}' if isinstance(x, float) else x) for k, x in r.items()})


def plot_trace(name, d, log, t0):
    t = (d['t'] - t0) * 1e6
    fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    ax[0].plot(t, d['v_ldo'], label='U1 OUT'); ax[0].plot(t, d['v_in'], label='eFuse IN')
    ax[0].plot(t, d['v_out'], label='+5V_IL'); ax[0].axhline(6.0, ls='--', c='r', lw=0.8, label='6.0 V abs max')
    ax[0].axhline(5.5, ls=':', c='r', lw=0.8, label='5.5 V ROC'); ax[0].set_ylabel('V'); ax[0].legend(fontsize=7)
    ax[1].plot(t, d['v_out'], label='+5V_IL'); ax[1].axhline(6.0, ls='--', c='r', lw=0.8)
    ax[1].axhline(5.5, ls=':', c='r', lw=0.8); ax[1].set_ylabel('+5V_IL (V)')
    lo, hi = np.nanmin(d['v_out'][d['t'] >= t0]), np.nanmax(d['v_out'][d['t'] >= t0])
    ax[1].set_ylim(min(lo, 4.0) - 0.1, max(hi, 6.1) + 0.1)
    ax[2].plot(t, d['v_p'], label='P'); ax[2].plot(t, d['v_shdn'], label='SHDN_c'); ax[2].plot(t, d['v_aux'], label='AUXOFF')
    ax[2].plot(t, d['v_vcb'] * 0.8, ls=':', label='0.8 VCB (CD)'); ax[2].axhline(0.8, ls='--', c='k', lw=0.8)
    ax[2].set_ylabel('V'); ax[2].legend(fontsize=7); ax[2].set_xlabel('time from event (us)')
    for a in ax:
        a.grid(alpha=0.3)
    fig.suptitle(f'{name} -- BEHAVIOURAL / PRELIMINARY (not hardware-validated)', fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / f'fig_{name}.png', dpi=110); plt.close(fig)


def main():
    quick = '--quick' in sys.argv
    OUT.mkdir(exist_ok=True); (OUT / 'traces').mkdir(exist_ok=True)
    t_start = time.time()
    nproc = min(16, max(1, (os.cpu_count() or 2) - 2))
    S = scenarios(quick)
    with ProcessPoolExecutor(nproc) as ex:
        res = list(ex.map(run_one, S))
    rows, logs = [], []
    for cfg, (m, log, d) in zip(S, res):
        rows.append(m)
        t0 = cfg.t_fault if cfg.t_fault < math.inf else 0.0
        logs.append(f'## {cfg.name}\n' + '\n'.join(f'  {(t - t0) * 1e6:12.3f} us  {x}' for t, x in log))
        if d is not None:
            sel = np.unique(np.linspace(0, len(d['t']) - 1, min(len(d['t']), 6000)).astype(int))
            write_csv(OUT / 'traces' / f'{cfg.name}.csv',
                      [{k: float(d[k][i]) for k in ('t', 'v_vin', 'v_ldo', 'v_in', 'v_out', 'v_vcb', 'v_p', 'v_shdn',
                                                     'v_aux', 'v_mr', 'v_x', 'i_f', 'i_s', 'i_ps')} for i in sel])
            dd = d
            if cfg.name.startswith(('TR_G2', 'TR_G5', 'TR_G8')):
                k = dd['t'] <= t0 + 60e-6
                dd = {kk: vv[k] for kk, vv in d.items()}
            plot_trace(cfg.name, dd, log, t0)
    write_csv(OUT / 'runs.csv', rows)
    sw = sweeps(quick)
    with ProcessPoolExecutor(nproc) as ex:
        srows = list(ex.map(_sweep_one, sw))
    write_csv(OUT / 'sweeps.csv', srows)
    bis = [(cn, kw, lim) for cn, kw in (('hard_cmin', dict(r_short=0.01, **CMIN)), ('hard_nom', {'r_short': 0.01}),
                                        ('hard_noL_cmin', dict(r_short=0.01, l_cab=1e-9, **CMIN)),
                                        ('rs1_edge1us_cmin', dict(r_short=1.0, t_edge=1e-6, **CMIN)),
                                        ('proposal_hard_cmin', dict(r_short=0.01, **{**CMIN, **PROPOSAL})))
           for lim in (5.5, 6.0)]
    if quick:
        bis = bis[:2]
    with ProcessPoolExecutor(nproc) as ex:
        brows = [{'case': a, 'limit_V': b, 'max_t_off_us': c} for a, b, c in ex.map(bisect_limit, bis)]
    write_csv(OUT / 'limits.csv', brows)
    # sweep figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cn in dict.fromkeys(r['case'] for r in srows if r['kind'] == 'ovlo_noFT'):
        xs = [(r['x_us'], r['pk_v_out']) for r in srows if r['kind'] == 'ovlo_noFT' and r['case'] == cn]
        ax.semilogx(*zip(*xs), marker='o', label=cn)
    ax.axhline(5.5, ls=':', c='r'); ax.axhline(6.0, ls='--', c='r'); ax.axvline(1.2, c='grey', lw=0.8)
    ax.text(1.25, ax.get_ylim()[0] + 0.05, 'tOVLO 1.2 us TYP (no max)', fontsize=7)
    ax.set_xlabel('HYPOTHETICAL eFuse turn-off delay after OVLO trip, fast-trip ignored (us)')
    ax.set_ylabel('peak +5V_IL (V)'); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    ax.set_title('A-IL12 sensitivity -- BEHAVIOURAL; sweep values are not datasheet limits', fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / 'fig_sweep_tovlo.png', dpi=110); plt.close(fig)
    (OUT / 'sim_log.txt').write_text('\n\n'.join(logs) + '\n')
    env = {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__,
               'matplotlib': matplotlib.__version__, 'platform': platform.platform(), 'quick': quick, 'n_runs': len(S),
               'n_sweep': len(sw), 'n_bisect': len(bis), 'wall_s': round(time.time() - t_start, 1),
               'command': 'python3 -I run_sim.py' + (' --quick' if quick else '')}
    (OUT / 'summary.json').write_text(json.dumps({'env': env, 'limits': brows}, indent=1) + '\n')
    print(json.dumps(env, indent=1))


if __name__ == '__main__':
    main()
