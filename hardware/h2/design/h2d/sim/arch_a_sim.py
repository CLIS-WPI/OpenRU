"""H2-D candidate A: behavioural check of the per-chain crowbar break-before-make (BBM) and the
50 us drain-discharge budget.  BEHAVIOURAL / PRELIMINARY -- not hardware-validated.

What is modelled (one chain + the shared permit node P):
  +5V_IL (TPS7A25 5.0 V, +-1 %) -> Rpu 2.2k -> P (C_P) ; faults pull P low through an OD (50 ohm ~ VOL 0.25 V @ 5 mA)
  VCB = +5V_IL via 100 ohm / 10 uF hold-up (1.5 mA domain load) (crowbar-timing domain)
  CD  : comparator, P < 0.8*VCB  -> Q_sd pulls SHDN_c low (fast path)
  SHDN_c = P via R_s 47k, R_sd 47k to GND, C_s 1n, + TPS1663 SHDN internal source (<= 10 uA)
  eFuse FET "possibly on" (conservative): on immediately when SHDN_c > 0.8 V; off only 1.5 us (tSD max)
        after SHDN_c falls below 0.8 V.  Pass current limited to ILIM max 2.16 A.
  CA  : comparator, SHDN_c > 0.1*VCB -> Q_t discharges C_t (timer reset)
  Timer: R_t from VCB charges C_t ; CB: V(C_t) > 0.5*VCB -> crowbar buffer -> crowbar gate (20 ohm, 340 pF)
  Crowbar: CSD16301Q2 + 6 x 1 ohm (0.1667 ohm); conductance ramps from VGS 0.9 V to 4.5 V.
  Drain: C_drain (max 23.8 uF), optional PA load.
Comparator delay is an ideal delay line of tpd (0 or 55 ns), VIO applied in the unsafe direction.
Run:  env -u LD_LIBRARY_PATH python3 -I arch_a_sim.py   (writes cases/*.cir, *.dat, results.md)
"""
import itertools, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NGRUN = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'sim', 'ngrun.py')
OUT = os.path.join(HERE, 'cases'); os.makedirs(OUT, exist_ok=True)

def tline(name, a, b, td):
    """ideal delay a->b (matched), td in seconds; td==0 -> plain buffer"""
    if td <= 0:
        return f"E{name} {b} 0 {a} 0 1\n"
    return (f"E{name}i {name}_i 0 {a} 0 1\nR{name}s {name}_i {name}_s 50\n"
            f"T{name} {name}_s 0 {name}_o 0 Z0=50 TD={td}\nR{name}l {name}_o 0 50\nE{name}o {b} 0 {name}_o 0 2\n")

def netlist(c):
    tt = c['tend']
    s = f"* H2-D arch A BBM case {c['name']} -- BEHAVIOURAL / PRELIMINARY\n"
    s += f"V5IL v5il 0 PWL({c['v5il']})\nVPAIN pain 0 {c['vin']}\n"
    s += "RH v5il vcb 100\nCH vcb 0 10u IC=4.9\nRLD vcb 0 3.3k\n"
    # permit node P
    s += f"RPU v5il p {c['rpu']}\nCP p 0 {c['cp']} IC={5.05 if c['armed0'] else 0}\n"
    s += f"VFLT flt 0 PWL({c['fault']})\n"            # 1 = some OD source asserts (pull low)
    s += "BPD p 0 I=V(flt)>0.5 ? V(p)/50 : 0\n"
    # CD: P < 0.5*VCB  (unsafe-direction VIO: trips later -> threshold lower)
    s += f"BCD cd_r 0 V=V(p) < (0.8*V(vcb) - {c['vio']}) ? V(vcb) : 0\n" + tline('cd', 'cd_r', 'cd', c['tpd'])
    s += "BQSD shdn 0 I=V(cd)>2 ? V(shdn)/10 : 0\n"
    # SHDN_c network
    s += f"RS p shdn {c['rs']}\nRSD shdn 0 {c['rsd']}\nCS shdn 0 {c['cs']} IC={2.5 if c['armed0'] else 0}\n"
    s += "BSRC 0 shdn I=V(shdn)<2.48 ? 10u : 0\n"          # TPS1663 SHDN internal source, worst 10 uA
    # eFuse FET possibly-on (conservative)
    s += "BSN sn 0 V=V(shdn)>0.8 ? 1 : 0\n" + tline('sd', 'sn', 'snd', 1.5e-6)
    s += "BFON fon 0 V=max(V(sn),V(snd))>0.5 ? 1 : 0\n"
    s += "BPASS pain vout I=V(fon)*min(max((V(pain)-V(vout))/0.053,0),2.16)\n"
    # drain
    s += f"CDR vout 0 {c['cdr']} IC={c['v0']}\n"
    if c['ipa'] > 0:
        s += f"BPA vout 0 I={c['ipa']}*min(V(vout)/0.5,1)\n"
    # CA: SHDN > 0.1*VCB -> timer reset ; unsafe VIO = threshold higher
    s += f"BCA ca_r 0 V=V(shdn) > (0.1*V(vcb) + {c['vio']}) ? V(vcb) : 0\n" + tline('ca', 'ca_r', 'ca', c['tpd'])
    s += "BQT ct 0 I=V(ca)>2 ? V(ct)/10 : 0\n"
    s += f"RT vcb ct {c['rt']}\nCT ct 0 {c['ct']} IC={0 if c['armed0'] else 5.0}\n"
    s += f"BCB cb_r 0 V=V(ct) > (0.5*V(vcb) - {c['vio']}) ? V(vcb) : 0\n" + tline('cb', 'cb_r', 'cb', c['tpd'])
    s += tline('bf', 'cb', 'drv', 6e-9)
    s += f"RDRV drv gate 20\nCG gate 0 340p IC={0 if c['armed0'] else 5.0}\n"
    s += "BCBR vout 0 I=V(vout)*max(0,min(1,(V(gate)-0.9)/3.6))/(0.1684+0.058)\n"
    s += "BOV ov 0 V=V(fon)*(V(gate)>0.3 ? 1 : 0)\n"
    s += f".tran 2n {tt} 0 5n UIC\n.end\n"
    return s

VEC = ['v(p)', 'v(shdn)', 'v(fon)', 'v(gate)', 'v(vout)', 'v(ov)', 'v(ct)', 'v(vcb)']

def run(c):
    cir = os.path.join(OUT, c['name'] + '.cir'); dat = os.path.join(OUT, c['name'] + '.dat')
    open(cir, 'w').write(netlist(c))
    r = subprocess.run(['python3', NGRUN, cir, dat] + VEC, cwd=OUT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    d = np.loadtxt(dat)
    t = d[:, 0]; v = {k: d[:, 2 * i + 1] for i, k in enumerate(VEC)}
    return t, v

def metrics(c, t, v):
    dt = np.diff(t, prepend=t[0])
    ov = float(np.sum(dt * (v['v(ov)'] > 0.5)))
    tf = c['tfault']
    m = {'overlap_us': ov * 1e6}
    # drain < 0.5 V: last time VOUT >= 0.5 V after the fault
    after = t >= tf
    hi = np.where(after & (v['v(vout)'] >= 0.5))[0]
    m['t50_us'] = (t[hi[-1]] - tf) * 1e6 if len(hi) else 0.0
    # BBM margin: crowbar gate first > 0.3 V minus FET-possibly-on end, after the fault
    g = np.where(after & (v['v(gate)'] > 0.3))[0]
    f = np.where(after & (v['v(fon)'] > 0.5))[0]
    if len(g) and len(f):
        m['bbm_margin_us'] = (t[g[0]] - t[f[-1]]) * 1e6
    return m

def corners():
    base = dict(rpu='2.2k', cp='100p', vin=5.5, v0=5.5, cdr='23.8u', ipa=0.0, armed0=True)
    tim = {'tmin': ('4249', '0.948n'), 'tmax': ('4391', '1.052n')}
    rc_s = {'slow': ('47.5k', '1.05n'), 'fast': ('46.5k', '0.95n')}
    for (tk, (rt, ct)), (sk, (rs, cs)), tpd, vio in itertools.product(tim.items(), rc_s.items(), (0.0, 55e-9), (0.0, 0.006)):
        yield dict(base, rt=rt, ct=ct, rs=rs, rsd=rs, cs=cs, tpd=tpd, vio=vio, tag=f"{tk}_{sk}_tpd{int(tpd*1e9)}_vio{int(vio*1e3)}")

def scenarios():
    T0 = 20e-6
    # S1: OD fault (supervisor / comparator / watchdog / FLT) asserts at T0 (detection delay excluded; added in budget)
    yield 'S1_odfault', dict(v5il='0 5.05', fault=f'0 0 {T0} 0 {T0+1e-9} 1', tfault=T0, tend=80e-6)
    # S2: arm rising edge: P held low from t=0 (crowbar active, drain 0), released at 20 us, then fault at 60 us
    yield 'S2_arm_edge', dict(v5il='0 5.05', fault=f'0 1 {T0} 1 {T0+1e-9} 0 60e-6 0 {60e-6+1e-9} 1', tfault=60e-6, tend=120e-6, v0=0.0, armed0=False)
    # S3: +5V_IL collapse at different slopes (monitor outputs treated as RELEASED = pessimistic)
    for sl in (0.01, 0.05, 0.1, 0.3, 1.0, 5.0, 50.0):         # V/us
        tfall = 5.05 / sl * 1e-6
        yield f'S3_il_collapse_{sl}Vus', dict(v5il=f'0 5.05 {T0} 5.05 {T0+tfall} 0', fault='0 0', tfault=T0,
                                             tend=T0 + tfall + 80e-6)
    # S4: short permit glitches (P released high for w, then pulled low again) while crowbar active
    for w in (0.2e-6, 0.5e-6, 1e-6, 2e-6, 5e-6, 20e-6):
        yield f'S4_glitch_{w*1e6:g}us', dict(v5il='0 5.05', fault=f'0 1 {T0} 1 {T0+1e-9} 0 {T0+w} 0 {T0+w+1e-9} 1',
                                            tfault=T0 + w, tend=T0 + w + 60e-6, v0=0.0, armed0=False)

def main():
    rows = []
    for (sname, sc), cc in itertools.product(list(scenarios()), list(corners())):
        c = dict(cc); c.update(sc); c['name'] = f"{sname}__{cc['tag']}"
        t, v = run(c); m = metrics(c, t, v)
        rows.append((sname, cc['tag'], m))
        os.remove(os.path.join(OUT, c['name'] + '.dat'))
    # summary per scenario
    lines = ['# Candidate A BBM / discharge check -- BEHAVIOURAL / PRELIMINARY', '',
             'Times from the instant the OD fault source asserts (S1, S2), the +5V_IL ramp starts (S3) or the glitch ends (S4).',
             'Detection delay of the source (e.g. TPS3703 tPD <= 30 us) is NOT included; add it from the budget table.', '',
             '| Scenario | corners | max overlap (us) | worst drain<0.5 V (us) | min BBM margin (us) |', '|---|---|---|---|---|']
    for s in dict.fromkeys(r[0] for r in rows):
        ms = [r[2] for r in rows if r[0] == s]
        ov = max(m['overlap_us'] for m in ms); t50 = max(m['t50_us'] for m in ms)
        bb = [m['bbm_margin_us'] for m in ms if 'bbm_margin_us' in m]
        lines.append(f"| {s} | {len(ms)} | {ov:.3f} | {t50:.2f} | {min(bb):.2f} |" if bb else
                     f"| {s} | {len(ms)} | {ov:.3f} | {t50:.2f} | n/a |")
    open(os.path.join(HERE, 'arch_a_results.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    assert all(r[2]['overlap_us'] == 0.0 for r in rows), 'BBM violated in some run'

if __name__ == '__main__':
    main()
