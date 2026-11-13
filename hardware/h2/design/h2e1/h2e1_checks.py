"""H2-E.1 DERIVED checks: TPS3703 SENSE protection options (A-SENSE) and E1-E5 gate/budget consistency.
Imports the H2-D budget unchanged. Run: python3 -I h2e1_checks.py  (exits non-zero on any failed assert)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'h2d' / 'sim'))
import budget as B  # noqa: E402

ABSMAX_SENSE, ROC_SENSE = 6.0, 5.5           # SBVS249B 7.1 / 7.3
ADTR_VDD_ABSMAX = 5.5
EFUSE_ROC_MIN = 4.5                           # TPS1663 VIN recommended min, SLVSET9G
PA_RAIL = (4.85, 5.18)                        # tile +5V_PA worst case, POWER_SPEC (H2-C)
V_FAULT = (12.0, 13.2)                        # FB-open: +5V_PA -> VIN; 13.2 V = 12 V +10 % (assumed input tolerance)
ISENSE_MAX = 1.5e-6                           # A at VSENSE = 5 V; NOT specified at 0.5 V (bypass mode) -> assumption
TCR_SPAN = 50e-6 * 65                         # two 25 ppm/K resistors, opposite drift, 25 C -> -40 / +85 C

def window(vit_nom, tol, acc, rtop, rbot, rtol=0.001):
    k = rbot / (rtop + rbot)
    rth = rtop * rbot / (rtop + rbot)
    ratio = 2 * rtol * (1 - k) + TCR_SPAN * (1 - k)          # worst-case divider ratio error
    isense = ISENSE_MAX * rth / (vit_nom * (1 - tol))       # current out of the divider pulls SENSE low -> trip points rise
    lo, hi = 1 - acc - ratio, 1 + acc + ratio + isense
    uv, ov = vit_nom * (1 - tol) / k, vit_nom * (1 + tol) / k
    return dict(k=k, uv=(uv * lo, uv, uv * hi), ov=(ov * lo, ov, ov * hi), vmax_roc=ROC_SENSE / k,
                sense_at_fault=[v * k for v in V_FAULT])

opts = {
    'H2-E as drawn: TPS3703A7330, 5.49k/10.7k, BAS116 to +5V_IL': window(3.30, 0.07, 0.007, 5.49e3, 10.7e3),
    'Option 1: TPS3703B6050, 18.0k/2.00k, no clamp':               window(0.50, 0.06, 0.010, 18.0e3, 2.00e3),
    'Option 2 (SELECTED): TPS3703A7120-Q1, 3.16k/1.00k, no clamp': window(1.20, 0.07, 0.007, 3.16e3, 1.00e3),
}
SEL = 'Option 2 (SELECTED): TPS3703A7120-Q1, 3.16k/1.00k, no clamp'
if __name__ == '__main__':
    for name, w in opts.items():
        print(name)
        print(f"  k {w['k']:.4f}; UV {w['uv'][0]:.3f}/{w['uv'][1]:.3f}/{w['uv'][2]:.3f} V; OV {w['ov'][0]:.3f}/{w['ov'][1]:.3f}/{w['ov'][2]:.3f} V (min/nom/max)")
        print(f"  SENSE at +5V_PA 12 / 13.2 V: {w['sense_at_fault'][0]:.2f} / {w['sense_at_fault'][1]:.2f} V; ROC kept up to +5V_PA = {w['vmax_roc']:.1f} V")
        print(f"  margins: UVmax->rail min {PA_RAIL[0]-w['uv'][2]:+.3f} V, rail max->OVmin {w['ov'][0]-PA_RAIL[1]:+.3f} V, "
              f"OVmax->5.5 V {ADTR_VDD_ABSMAX-w['ov'][2]:+.3f} V, UVmin->eFuse ROC {w['uv'][0]-EFUSE_ROC_MIN:+.3f} V")
    o1 = opts[SEL]
    assert max(o1['sense_at_fault']) <= ROC_SENSE                       # no ROC/abs-max violation, no clamp, no back-power
    assert o1['ov'][2] < ADTR_VDD_ABSMAX and o1['uv'][0] > EFUSE_ROC_MIN
    assert o1['uv'][2] < PA_RAIL[0] and o1['ov'][0] > PA_RAIL[1]        # no static nuisance trip on the tile rail spec
    old = opts['H2-E as drawn: TPS3703A7330, 5.49k/10.7k, BAS116 to +5V_IL']
    assert old['sense_at_fault'][0] > ROC_SENSE                         # the H2-E exposure is real

    # ---- E1-E5 gate audit against the H2-D budget ----
    chain = B.P_FALL + B.tail + B.t_dis(5.5)                          # P low -> drain < 0.5 V
    pre_dis = B.P_FALL + B.tail
    print(f"\nbudget: rail row {B.A['rail UV/OV (TPS3703)']:.2f} us, chain after P {chain:.3f} us, d_min {B.d_min:.3f} us, "
          f"BBM fall {B.bbm_fall_min:.3f} us, BBM rise {B.bbm_rise_min:.3f} us")
    assert abs(chain - 16.5) < 0.01 and abs(B.A['rail UV/OV (TPS3703)'] - 46.5) < 0.01
    # E1: HOLD upper bound vs BENCH_PLAN T7 (BBM_fall >= 1.0 us)
    e1_hold_old = 0.75 * B.d_min
    e1_hold_new = B.d_min - 1.0
    print(f"E1 HOLD ceiling 0.75*d_min = {e1_hold_old:.3f} us leaves BBM_fall {B.d_min-e1_hold_old:.3f} us < 1.0 us (T7) "
          f"-> corrected ceiling d_min - 1.0 = {e1_hold_new:.3f} us")
    assert B.d_min - e1_hold_old < 1.0 and abs(B.d_min - e1_hold_new - 1.0) < 1e-9
    # E2: RDS(on) kill bound
    t_dis_allow = 50 - B.TPS3703_TPD - pre_dis
    from math import log
    r_loop = t_dis_allow / log(5.5 / 0.5) / B.C_MAX
    print(f"E2 kill bound: discharge allowance {t_dis_allow:.2f} us -> R_loop <= {r_loop:.4f} ohm -> RDS(on) <= {r_loop-B.R_CB:.4f} ohm")
    assert abs((r_loop - B.R_CB) - 0.120) < 0.001
    # E5 on the fixture: RS3 10 mOhm shunt sits in the crowbar loop
    tau_fix = (B.R_CB + B.RDS + 0.010) * B.C_MAX
    chain_fix = pre_dis + tau_fix * log(5.5 / 0.5)
    print(f"E5 t_chain with RS3 in loop at placeholder RDS: {chain_fix:.2f} us (> 16.5 GO limit) -> measure with RS3 force pads shorted")
    assert chain_fix > 16.5
    # E3 HOLD band and E5 NO-GO edge
    print(f"E3 HOLD band if E5 chain = 16.5: 30 .. {50-chain:.2f} us; E5 t_chain NO-GO edge with DS 30 us: {50-30:.1f} us")
    # E3 slow-ramp gap: 5 % overdrive point of the selected UV (min) relative to eFuse ROC
    uv5 = o1['uv'][0] * 0.95
    print(f"E3 slow ramp: 5 % overdrive below UV(min) is {uv5:.3f} V < eFuse ROC {EFUSE_ROC_MIN} V -> add gate E3c")
    assert uv5 < EFUSE_ROC_MIN
    # R57/R58 CA reference: 9.09k/1.01k (E192, not stocked) -> 18.0k/2.00k (E24, 0.1 %, 25 ppm)
    k_old, k_new = 1.01 / (9.09 + 1.01), 2.00 / (18.0 + 2.00)
    rth_new = 18.0e3 * 2.00e3 / 20.0e3
    ib_err = 5e-9 * rth_new                                         # TLV3201/3202 IIB max -40..125 C, SBOS561C
    print(f"CA divider k {k_old:.5f} -> {k_new:.5f}; bias error {ib_err*1e6:.1f} uV vs VIO 6000 uV in budget; "
          f"VCB load {B.VCB_MIN/10.1e3*1e3:.3f} -> {B.VCB_MIN/20e3*1e3:.3f} mA (lower load: VCB_MIN unchanged-safe)")
    assert abs(k_new - 0.1) < 1e-12 and abs(k_old - 0.1) < 1e-12 and ib_err < 0.01 * 0.006
    # divider dissipation at the fault voltage (0603 thin film, 0.1 W)
    p_top = (V_FAULT[1] * (1 - o1['k'])) ** 2 / 3.16e3
    print(f"R10 3.16k dissipation at +5V_PA 13.2 V: {p_top*1e3:.0f} mW (0.1 W rating)")
    assert p_top < 0.05
    print("ALL CHECKS PASS")
