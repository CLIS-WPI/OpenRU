"""A-IL12 analytic checks (DERIVED from params.py; tags carried into the output).
Run: python3 -I calc.py  -> out/calc.txt, out/calc.json ; exits non-zero if a self-check assert fails.
Asserts check arithmetic and the study's stated conclusions; they do NOT certify the design."""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'h2d' / 'sim'))
from params import P, v

OUT = HERE / 'out'
R = {}
lines = []


def say(s=''):
    lines.append(s)


def rec(key, val, tag):
    R[key] = {'value': val, 'tag': tag}
    return val


def div_k(rt, rb, tol=0.001, tcr=25e-6 * 2 * 100):
    """divider ratio min/nom/max with resistor tolerance and opposite TCR drift over 100 K"""
    e = tol + tcr / 2
    k = rb / (rt + rb)
    kmin = rb * (1 - e) / (rt * (1 + e) + rb * (1 - e))
    kmax = rb * (1 + e) / (rt * (1 - e) + rb * (1 + e))
    return kmin, k, kmax


def cap_corners():
    """+5V_IL, U1-output and eFuse-IN capacitance corners (F). Tolerance and X5R/X7R temperature from DS/EIA,
    DC-bias retention ASSUMED (no manufacturer curve read)."""
    t = v('x5r_temp')
    d47, d4u7, d100n = P['dcb_47u_1210_16v'].value, P['dcb_4u7_0603_10v'].value, P['dcb_100n_0402'].value
    out_min = 47e-6 * 0.8 * (1 - t) * d47[0] + 4.7e-6 * 0.9 * (1 - t) * d4u7[0] + 6 * 0.1e-6 * 0.9 * (1 - t) * d100n[0]
    out_nom = 47e-6 * 0.65 + 4.7e-6 * 0.5 + 6 * 0.1e-6 * 0.875
    out_max = 47e-6 * 1.2 + 4.7e-6 * 1.1 + 6 * 0.1e-6 * 1.1          # no DC-bias loss: worst for hold-up / decay time
    d2, din = P['dcb_4u7_0805_25v'].value, P['dcb_1u_0603_25v_hv'].value
    return {'c_out': (out_min, out_nom, out_max),
                'c2': (4.7e-6 * 0.9 * (1 - t) * d2[0], 4.7e-6 * 0.675, 4.7e-6 * 1.1),
                'c_in': (1e-6 * 0.9 * (1 - t) * din[0], 1e-6 * 0.475, 1e-6 * 1.1),
                'c5': (10e-6 * 0.9 * (1 - t) * 0.45, 10e-6 * 0.6, 10e-6 * 1.1)}


def main():
    say('# A-IL12 analytic checks (DERIVED unless tagged otherwise)')
    vf = v('v_fault', 1)
    vldo_min, _, vldo_max = v('vldo')
    R_IN = 2.2

    # ---- 1. OVLO divider 10.0k / 2.94k on U1 OUT ----
    k = div_k(10.0e3, 2.94e3)
    trip_r = (v('vov_r', 0) / k[2], v('vov_r', 1) / k[1], v('vov_r', 2) / k[0])
    trip_f = (v('vov_f', 0) / k[2], v('vov_f', 1) / k[1], v('vov_f', 2) / k[0])
    rec('ovlo_trip_rise_V', trip_r, 'DERIVED'); rec('ovlo_trip_fall_V', trip_f, 'DERIVED')
    margin = trip_r[0] - vldo_max
    rec('ovlo_margin_to_ldo_max_V', margin, 'DERIVED')
    say(f'\n## 1 OVLO divider 10.0k/2.94k (0.1 %, 25 ppm/K): k = {k[0]:.5f}/{k[1]:.5f}/{k[2]:.5f}')
    say(f'- trip rising {trip_r[0]:.3f}/{trip_r[1]:.3f}/{trip_r[2]:.3f} V, falling {trip_f[0]:.3f}/{trip_f[1]:.3f}/{trip_f[2]:.3f} V')
    say(f'- margin rising-min to U1 OUT max {vldo_max} V: {margin*1e3:.0f} mV (no false trip in normal operation)')
    for vv in (vf, 18.2):
        pin = vv * k[2]
        say(f'- OVLO pin at IN = {vv} V: {pin:.2f} V  (ROC max 1.5 V: {"EXCEEDED" if pin > 1.5 else "ok"}; abs max 6.5 V: '
            f'{"EXCEEDED" if pin > 6.5 else "ok"})')
    rec('ovlo_pin_at_13V2', vf * k[2], 'DERIVED')
    vmax_roc = 1.5 / k[2]
    say(f'- OVLO pin stays inside the 0.5-1.5 V ROC only up to IN = {vmax_roc:.2f} V. Above that the pin is outside the '
        'characterised range (EC rows only cover 0.5-1.5 V). Abs max 6.5 V is kept up to '
        f'{6.5 / k[2]:.1f} V. TI behaviour for 1.5 < VOVLO <= 6.5 V: UNSPECIFIED (question for TI).')
    say(f'- divider power at {vf} V: {vf**2/12.94e3*1e3:.1f} mW total (0603 0.1 W ok)')
    say(f'- RECOVERY: OVLO releases only when U1 OUT < falling trip {trip_f[0]:.3f}-{trip_f[2]:.3f} V. With U1 back in '
        f'regulation ({vldo_min}-{vldo_max} V) the release is NOT determined: at most corners U1 OUT stays above the '
        f'falling trip and the eFuse stays off (hysteresis acts as a de-facto latch until IN is cycled); at the corner '
        f'VOV(F) max + k min + U1 OUT min ({trip_f[2]:.3f} > {vldo_min}) it auto-recovers after tSWOV (90 us TYP). '
        'Neither latching nor recovery is guaranteed.')
    rec('ovlo_recovery_ambiguous', trip_f[2] > vldo_min and trip_f[0] < vldo_max, 'DERIVED')
    assert trip_f[0] < vldo_min < trip_f[2] < vldo_max
    assert margin > 0.05

    # ---- 2. "BZX84C1V5" clamp ----
    ir, vr = v('bzx84c2v4_ir')
    i_div = v('vov_r', 1) / 2.94e3
    say('\n## 2 Proposed OVLO clamp "BZX84C1V5"')
    say('- BZX84 series (Diodes DS18001; onsemi BZX84C2V4LT1/D) starts at 2V4. No 1V5 type is listed: the MPN is '
        'treated as NON-EXISTENT/UNVERIFIED (Nexperia page not retrievable from here).')
    say(f'- Nearest real part BZX84C2V4: VZ 2.2-2.6 V at 5 mA -> cannot hold the pin <= 1.5 V ROC; IR up to {ir*1e6:.0f} uA '
        f'at {vr} V, i.e. up to {ir/i_div*100:.0f} % of the {i_div*1e6:.0f} uA divider current at the trip point '
        '-> raises the OVLO trip by an unbounded, temperature-dependent amount.')
    say('- A shunt reference (TLV431-class, 1.24 V) overlaps the OVLO rising threshold (max 1.223 V) within its own '
        'tolerance and could block the trip. Decision: NO clamp. The pin stays <= 3.0 V at 13.2 V (< 6.5 V abs max).')
    rec('bzx84c1v5', 'not found; removed', 'DS')

    # ---- 3. EN/UVLO divider 100k / 37.4k on U1 OUT ----
    ke = div_k(100e3, 37.4e3)
    uv_r = (v('vuvlo_r', 0) / ke[2], v('vuvlo_r', 2) / ke[0])
    uv_f = (v('vuvlo_f', 0) / ke[2], v('vuvlo_f', 2) / ke[0])
    say(f'\n## 3 EN/UVLO divider 100k/37.4k: k {ke[1]:.4f}; on {uv_r[0]:.2f}-{uv_r[1]:.2f} V, off {uv_f[0]:.2f}-{uv_f[1]:.2f} V')
    for vv in (vf, 18.2):
        say(f'- EN pin at IN = {vv} V: {vv*ke[2]:.2f} V (ROC 5 V, abs max 6.5 V)')
    say('- EN tied directly to IN (as the TPS7A25 EN is) would put 13.2 V on a 6.5 V abs-max pin in the fault: not allowed.')
    assert uv_r[1] < vldo_min and vf * ke[2] < 5.0
    rec('en_pin_at_13V2', vf * ke[2], 'DERIVED')

    # ---- 4. ILIM ----
    say('\n## 4 ILIM resistor')
    say(f'- 6.65 kOhm is the RILM ROC maximum ({v("rilm_roc", 1):.0f} Ohm); any + tolerance leaves the ROC. Candidate: '
        '6.49 kOhm 0.1 % (max 6.497 kOhm).')
    il = 3334 / 6490
    say(f'- ILIM (Eq. 7) {il:.3f} A typ. Guaranteed limits exist only at the EC test points; scaling the 6.65 k row '
        f'(+-15 %) gives {il*0.85:.3f}-{il*1.15:.3f} A (DERIVED, not guaranteed). Fast-trip ISC = 2.01 x ILIM (DS-TYP '
        f'only) ~ {2.01*il:.2f} A. U1 ICL min 0.325 A < ILIM: a downstream overload is limited by U1, not the eFuse.')
    rec('ilim_A', (il * 0.85, il, il * 1.15), 'DERIVED')

    # ---- 5. IN slew rate with and without R_in ----
    cc = cap_corners()
    cin_min = cc['c_in'][0]
    sr_r = (vf - vldo_min) / (R_IN * cin_min)
    sr_f = vldo_max / (R_IN * cin_min)
    say('\n## 5 eFuse IN slew-rate abs max (SRIN(R) 100 V/us, SRIN(F) 10 V/us)')
    say(f'- With R_in {R_IN} Ohm + C_in (1 uF 25 V X7R, eff min {cin_min*1e6:.2f} uF ASSUMED): rising <= '
        f'{sr_r/1e6:.1f} V/us, falling (U1 OUT hard-shorted to GND) <= {sr_f/1e6:.1f} V/us. Upper bounds for any R_short.')
    c2p = 4.7e-6 * 0.9 * 0.85 * P['dcb_4u7_0603_10v'].value[0]
    rmin = (vf - 5.0) / (v('sr_in_r') * c2p)
    say(f'- Proposal (IN = U1 OUT, only C2 4.7 uF 10 V, eff min {c2p*1e6:.2f} uF): initial slew = (VIN - 5 V)/(R_short C2). '
        f'Exceeds 100 V/us for R_short < {rmin*1e3:.0f} mOhm (any short harder than that VIOLATES SRIN(R)). R_short is unbounded.')
    assert sr_r < v('sr_in_r') and sr_f < v('sr_in_f')
    rec('sr_in_rise_bound_Vus', sr_r / 1e6, 'DERIVED'); rec('sr_in_fall_bound_Vus', sr_f / 1e6, 'DERIVED')
    rec('proposal_rshort_min_for_100Vus_mohm', rmin * 1e3, 'DERIVED')
    vdrop = 15e-3 * (R_IN + v('ron_max'))
    say(f'- Cost: +5V_IL drop at 15 mA (ASSUMED max) {vdrop*1e3:.0f} mV. R_in pulse at OVLO recovery (current-limited '
        f'start, <= {il*1.15:.2f} A): {(il*1.15)**2*R_IN:.2f} W for <= {cc["c_out"][2]*5.08/(il*0.85)*1e3:.2f} ms '
        f'-> {(il*1.15)**2*R_IN*cc["c_out"][2]*5.08/(il*0.85)*1e3:.2f} mJ (use a 1206 pulse-rated part; rating NOT verified).')

    # ---- 6. capacitor voltage ratings ----
    say('\n## 6 Capacitor voltage ratings in the fault (IN side reaches VIN, 13.2 V; sim peak with cable L: see sim)')
    say('- Fixture C2 CL10A475KP8NNNC is 10 V: OVER-STRESSED at 12-13.2 V. Candidate: CL21A475KAQNNNE 4.7 uF 25 V X5R 0805.')
    say(f'- dVdt capacitor rating >= VIN + 5 V = {vf+5:.1f} V -> 2.2 nF 50 V C0G. C_in 1 uF 25 V. +5V_IL caps stay low-voltage.')

    # ---- 7. capacitance after inserting the disconnect ----
    say('\n## 7 Capacitance (F) after the disconnect (DC-bias retention ASSUMED, see params.py)')
    for kk, (a, b, c) in cc.items():
        say(f'- {kk}: min {a*1e6:.2f} / nom {b*1e6:.2f} / max {c*1e6:.2f} uF')
    tot_nom = 4.7 + 1.0 + 4.7 + 47 + 0.6 + 10
    say(f'- U1 (TPS7A2550) sees C2 locally (4.7 uF nominal >= 2.2 uF with TI 50 % derating rule). With the eFuse on it also '
        f'sees C_in, +5V_IL and C5 via R1: {tot_nom:.1f} uF nominal <= 100 uF COUT max.')
    say('- Before the change C2 + C3 (2 x 4.7 uF) sat directly on U1 OUT; C3 now sits on +5V_IL behind the eFuse.')
    assert tot_nom <= 100
    rec('c_out_uF', tuple(x * 1e6 for x in cc['c_out']), 'DERIVED/ASSUMED')
    sr = (v('idvdt', 0) * v('sr_gain', 0) / 2.2e-9, v('idvdt', 2) * v('sr_gain', 2) / 2.2e-9)
    say(f'- dVdt 2.2 nF: SR {sr[0]/1e3:.2f}-{sr[1]/1e3:.2f} V/ms (DERIVED from typ table x IdVdt limits); inrush <= '
        f'{sr[1]*cc["c_out"][2]*1e3:.1f} mA; ramp to 5 V {5/sr[1]*1e3:.1f}-{5/sr[0]*1e3:.1f} ms.')

    # ---- 8. BSS84 interface (proposal) ----
    say('\n## 8 Proposal: AUXOFF -> BSS84 gate, source = P, drain = GND')
    vth = abs(v('bss84_vth', 1))
    i_pu = (vldo_max - 0.8) / v('r2_pu')
    say(f'- The PMOS conducts only while VSG = V(P) - V(AUXOFF) > |VGS(th)|. With AUXOFF at 0 V, P cannot fall below '
        f'|VGS(th)|: min |VGS(th)| = {vth} V at 250 uA, 25 C (DS) > 0.8 V. At the real sink current '
        f'(~{i_pu*1e3:.1f} mA through R2) P settles higher still.')
    for vt in (0.9, 2.0):
        kp = 1 / (v('bss84_rds') * (5 - vt))
        for vol in (0.0, 0.3):
            # saturation: I = k/2 (VSG - Vt)^2 with VSG = P - vol, I = (5.08 - P)/2.2k  -> solve
            f = lambda p, kp=kp, vol=vol, vt=vt: 0.5 * kp * max(0, p - vol - vt) ** 2 - (vldo_max - p) / v('r2_pu')
            lo, hi = 0.0, vldo_max
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
            say(f'  |Vth| {vt} V, AUXOFF low {vol} V: P = {lo:.2f} V (level-1 fit to RDS(on) max; BEHAVIOURAL)')
            assert lo > 0.8
    say('- RESULT: P <= 0.8 V is NOT guaranteed; it is guaranteed NOT to be reached at 25 C (P >= 0.9 V). Hot-temperature '
        'VGS(th) is not specified. The BSS84 can still pull P below 0.8 x VCB (CD trip ~3.9 V), so the CD path may '
        'shut the PA; P itself stays in an undefined logic region.')
    rec('bss84_guarantees_P_le_0V8', False, 'DERIVED')

    # ---- 9. corrected interface DC checks ----
    ra, rb = 100e3, 1.0e6
    say('\n## 9 Corrected interface (AUXOFF -> 100k/1M -> Q_A 2N7002 -> X (10k to +5V_IL) -> Q_B on U3 MR, Q_C on P)')
    say(f'- AUXOFF high level {vldo_max*rb/(ra+rb):.2f} V <= 5 V ROC (pull-up to +5V_IL alone would be up to {vldo_max} V).')
    say(f'- Q_A on: VGS >= {4.603*rb/(ra+rb):.2f} V (at +5V_IL = U3 UV min) vs VGS(th) max 2.5 V. rDS(on) is specified only at '
        'VGS 5 V (7.5 Ohm, 25 C; 13.5 Ohm 125 C).')
    say('- Q_A off needs V(AUXOFF low) < VGS(th) min 1.0 V (25 C). AUXOFF VOL is NOT specified (0 V typ with VIN > UVP; '
        '0.67-1.0 V unpowered at 26-242 uA) -> UNBOUNDED; bench gate.')
    rq = 0.8 / ((vldo_max - 0.8) / v('r2_pu'))
    say(f'- P <= 0.8 V through Q_C needs rDS <= {rq:.0f} Ohm (7.5 Ohm max at VGS 5 V; VGS ~ +5V_IL here). Guaranteed path: '
        'U3 RESET VOL <= 0.25 V at >= 3 mA (VDD >= 2 V) once MR is seen low; tPD(MR) 500 ns TYP only.')
    say(f'- MR <= 0.3 V (VMR_L) through Q_B against RMR 100 k (typ only): needs rDS <= {0.3/(vldo_max/100e3)*0.8:.0f} Ohm '
        'if RMR were 20 % lower than typ (RMR min NOT specified).')
    say(f'- Added +5V_IL load in normal operation: {vldo_max/1.1e6*1e3:.3f} + {vldo_max/10e3*1e3:.2f} mA (R_X with Q_A on).')

    # ---- 10. back-power ----
    say('\n## 10 Back-power paths into +5V_IL')
    th_r = 10.7e3 * 5.49e3 / 16.19e3
    vth9 = 5.5 * 5.49 / 16.19
    say(f'- +5V_PA -> R39/R40 -> U9 IN+ ESD -> +5V_IL: Thevenin {vth9:.2f} V / {th_r/1e3:.2f} kOhm -> <= '
        f'{(vth9-0.3)/th_r*1e3:.2f} mA into a dead rail (< 10 mA input-current abs max); lifts +5V_IL <= ~{vth9-0.3:.1f} V '
        'unloaded: below TPS3703 UVLO 1.7 V (RESET held low) and U10 UVLO (3.88 V).')
    say('- J4 gate / negative-rail emulation through 49.9 k: <= 0.1 mA each.')
    say('- U4 SENSE (3.16k/1.00k from +5V_PA): SENSE behaviour with VDD = 0 NOT specified (ISENSE given only at 5 V).')
    say(f'- eFuse in OVLO with VIN > VOUT: forward off-state leakage NOT specified (IOUTLKG(OVLO) {v("ioutlkg_ovlo")*1e6:.0f} uA '
        'is the VOUT > VIN direction). +5V_IL cannot rise while leakage < its load; load with P low >= '
        f'{(4.6/2.2e3 + 1.5e-3 + v("i_il",0))*1e3:.1f} mA (R2 + VCB + ASSUMED 3 mA). Swept in the sim as HYPOTHETICAL.')
    say('- +5V_IL -> U1 OUT when VIN collapses: blocked by eFuse reverse-current blocking (no DC reverse current; tRCB 1 us TYP).')
    say('- AUXOFF pull-up into an unpowered eFuse: <= 51 uA through 100k (no active pull-down when unpowered).')

    # ---- 11. R4 timing: guaranteed path vs AUXOFF path ----
    import budget as B
    tail = B.P_FALL + B.tail + B.t_dis(5.5)
    say(f'\n## 11 Timing (H2-D tail from P sink asserted to drain < 0.5 V: {tail:.2f} us, budget.py)')
    cmax = cc['c_out'][2] + cc['c5'][2]
    uv_od = v('u3_uv', 0) * 0.95
    i_min = v('i_il', 0) + 1.5e-3
    t_uv = cmax * (vldo_max - uv_od) / i_min
    say(f'- Guaranteed fallback: +5V_IL must decay to U3 UV at 5 % overdrive ({uv_od:.2f} V). With C <= {cmax*1e6:.0f} uF and '
        f'load >= {i_min*1e3:.1f} mA (ASSUMED; P is still high so R2 does not load) this takes up to {t_uv*1e3:.1f} ms, '
        f'then tPD 30 us. From the short onset this is >> 50 us.')
    say('- Under the existing R4 definition (onset = monitored rail 5 % beyond its threshold) the +5V_IL row stays 46.5 us. '
        'During the decay +5V_IL is within ROC, so the permit logic remains valid; the PA stays enabled on a regulator '
        'that has already failed until then.')
    say(f'- If the onset is the short itself, the AUXOFF path must assert P within 50 - {tail:.1f} = {50-tail:.1f} us. '
        'AUXOFF de-assertion delay has NO specification -> not provable.')
    rec('u3_fallback_ms', t_uv * 1e3, 'DERIVED/ASSUMED'); rec('tail_us', tail, 'DERIVED')

    # ---- 12. H2-D budget with the added drop (VCB_MIN) ----
    src = (HERE.parent / 'h2d' / 'sim' / 'budget.py').read_text()
    old = 'VCB_MIN, VCB_MAX = 4.77, 5.08'
    assert old in src
    vcb_new = round(4.77 - vdrop, 3)
    g = {'__name__': 'budget_ail12'}
    exec(compile(src.replace(old, f'VCB_MIN, VCB_MAX = {vcb_new}, 5.08'), 'budget_ail12', 'exec'), g)  # noqa: S102 - unchanged H2-D budget, one input replaced
    say(f'\n## 12 H2-D budget re-evaluated with VCB_MIN {vcb_new} V (was 4.77 V; R_in + Ron drop at 15 mA)')
    say(f'- crowbar delay {g["d_min"]:.3f}-{g["d_max"]:.3f} us (was {B.d_min:.3f}-{B.d_max:.3f}); BBM falling '
        f'{g["bbm_fall_min"]:.3f} us (was {B.bbm_fall_min:.3f}); worst R4 row {max(g["A"].values()):.2f} us '
        f'(was {max(B.A.values()):.2f}).')
    assert max(g['A'].values()) < 50 and g['bbm_fall_min'] > 1.0
    rec('budget_worst_us', max(g['A'].values()), 'DERIVED')

    # ---- 13. analytic max permissible OVLO delay (fast-trip ignored) ----
    say('\n## 13 Max permissible eFuse turn-off delay (analytic, FT ignored, R_in present)')
    for vpk, lim in ((13.2, 5.5), (13.2, 6.0), (18.2, 5.5), (18.2, 6.0)):
        cmin = cc['c_out'][0]
        # OUT charges through R_in + Ron from a U1-OUT node held at vpk (upper bound on current)
        tau = (R_IN + v('ron_max')) * (cmin + cin_min)
        tmax = tau * math.log((vpk - vldo_max) / (vpk - lim))
        say(f'- U1 OUT at {vpk} V, limit {lim} V, C_out min {cmin*1e6:.1f} uF: t_off <= {tmax*1e6:.1f} us '
            '(HYPOTHETICAL-delay bound; compare tOVLO 1.2 us TYP, no max)')
        rec(f'tmax_analytic_{vpk}_{lim}', tmax * 1e6, 'DERIVED')

    OUT.mkdir(exist_ok=True)
    (OUT / 'calc.txt').write_text('\n'.join(lines) + '\n')
    (OUT / 'calc.json').write_text(json.dumps(R, indent=1) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
