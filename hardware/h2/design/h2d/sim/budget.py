"""H2-D worst-case R4 timing budgets and break-before-make bounds for candidates A and B.
DERIVED from datasheet min/max (sources in ARCH_COMPARE.md). Items marked PLACEHOLDER are NOT datasheet-bounded.
Run: python3 -I budget.py"""
from math import log

# ---- shared datasheet bounds ----
TPS3703_TPD = 30.0            # us max, 5 % overdrive, SBVS249B p7
TLV3202_TPD = 0.055           # us max, -40..125 C, 100 mV overdrive, SBOS561C p5/p6
LVC1G17_TPD = 0.0065          # us max at 5 V, SCES351Y p7
TPS1663_TSD = 1.5             # us max, SHDN below V(SHUTF) -> FET OFF, SLVSET9G p10
TPS1663_OVP_TOFF = 14.0       # us max, OVP -> FLT low, SLVSET9G p9
VCB_MIN, VCB_MAX = 4.77, 5.08 # +5V_IL (TPS7A25 +-1 %, line 0.1 %, load 0.5 %, SBVS372C p6) minus 100 ohm x 1.5 mA

# ---- crowbar timer (R_t 4.32k 1 % +-0.65 % TCR; C_t 1 nF C0G 5 % +-0.2 %; k_t = 0.5, 0.1 % divider, VIO 6 mV) ----
tau_min = 4.32 * (1 - 0.0165) * 1.0 * (1 - 0.052)
tau_max = 4.32 * (1 + 0.0165) * 1.0 * (1 + 0.052)
dk = 0.001 * 0.5 + 0.006 / VCB_MIN
k_min, k_max = 0.5 - dk, 0.5 + dk
d_min = tau_min * log(1 / (1 - k_min))
d_max = tau_max * log(1 / (1 - k_max))
t_gate = 2.8e-9 / 32e-3 * 1e6
cb_on_max = d_max + 2 * TLV3202_TPD + LVC1G17_TPD + t_gate
bbm_fall_min = d_min - TPS1663_TSD

# ---- rising edge: SHDN_c from Vref_cb(max) to 0.8 V through (R_s || R_sd) C_s ----
vref_max = 0.1 * VCB_MAX * 1.001 + 0.006
vh_max = 5.08 * 0.5 * 1.01 + 10e-6 * 23.5e3               # divider + TPS1663 SHDN source <= 10 uA
tau_s_min = 23.25e3 * 0.95e-9 * 1e6
t_rise_min = tau_s_min * log((vh_max - vref_max) / (vh_max - 0.8))
cb_off_max = 2 * TLV3202_TPD + 0.03 + LVC1G17_TPD + t_gate       # 0.03 us: Q_t discharge of C_t (10 ohm PLACEHOLDER)
bbm_rise_min = t_rise_min - cb_off_max

# ---- discharge of one chain ----
C_MAX = (4 * 4.7 + 1.0 + 0.01 + 0.0001) * 1.2                # uF, X5R/X7R +20 %
R_CB = (1.0 / 6) * 1.01                                        # 6 x RCS1206 1 ohm 1 %
RDS = 0.029 * 2.0                                              # PLACEHOLDER: 25 C max x 2 for temperature (typ curve only)
tau_d = (R_CB + RDS) * C_MAX
def t_dis(v0):
    return tau_d * log(v0 / 0.5)

P_FALL = 0.1                    # us: 100 pF permit node, >= 2.7 mA net sink (TPS3703 5 mA @ 0.25 V minus 2.3 mA pull-up)
CD_SHDN = TLV3202_TPD + 0.02    # CD + Q_sd discharge of C_s (10 ohm PLACEHOLDER)
tail = CD_SHDN + cb_on_max      # from P low to crowbar fully on (FET-off 1.5 us runs in parallel, inside d_min)

A = {
    'rail UV/OV (TPS3703)':          TPS3703_TPD + P_FALL + tail + t_dis(5.5),
    'gate lost (TLV3202 + NMOS)':    TLV3202_TPD + 0.05 + P_FALL + tail + t_dis(5.5),
    'TPS1663 OVP (+5V_PA OV)':       TPS1663_OVP_TOFF + P_FALL + tail + t_dis(6.3),
    'from FLT / WDO assertion':      P_FALL + 0.2 + tail + t_dis(5.5),
    '+5V_IL abrupt loss (CD path)':  0.5 + tail + t_dis(5.5),
}
# ---- candidate B: per-PA TPS22918 with C_local 0.1 uF (+10 %) + 10 nF + 100 pF, RPD <= 30 ohm at VIN 5 V ----
C_B = (0.1 * 1.1 + 0.01 + 0.0001)
t_qod = 30 * C_B * log(5.5 / 0.5)
B = {k: (TPS3703_TPD if 'rail' in k else TLV3202_TPD + 0.05) + P_FALL + t_qod for k in ('rail UV/OV (TPS3703)', 'gate lost (TLV3202 + NMOS)')}

if __name__ == '__main__':
    print(f"timer tau {tau_min:.3f}..{tau_max:.3f} us; crowbar delay {d_min:.3f}..{d_max:.3f} us; crowbar fully on <= {cb_on_max:.3f} us")
    print(f"BBM falling edge >= {bbm_fall_min:.3f} us (delay_min {d_min:.3f} - tSD_max {TPS1663_TSD})")
    print(f"BBM rising edge >= {bbm_rise_min:.3f} us (SHDN {vref_max:.3f}->0.8 V takes >= {t_rise_min:.3f} us; crowbar off <= {cb_off_max:.3f} us)")
    print(f"discharge tau {tau_d:.3f} us (C {C_MAX:.2f} uF, R {R_CB+RDS:.4f} ohm); 5.5 V->0.5 V {t_dis(5.5):.2f} us; peak {5.5/(R_CB+RDS):.1f} A; E {0.5*C_MAX*5.5**2:.0f} uJ")
    for k, v in A.items():
        print(f"A  {k:32s} {v:6.2f} us  margin {50-v:5.2f}")
    for k, v in B.items():
        print(f"B  {k:32s} {v:6.2f} us + TPS22918 tOFF (NO MAX)  ; QOD part {t_qod:.2f} us")
    assert bbm_fall_min > 1.0 and bbm_rise_min > 1.0 and all(v < 50 for v in A.values())
