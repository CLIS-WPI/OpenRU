"""A-IL12 parameter registry. Every number used by calc.py / model.py lives here with an evidence tag.

Tags:
  DS-MIN / DS-MAX   guaranteed datasheet limit (document, section)
  DS-TYP            datasheet typical value; NOT a guaranteed limit
  DERIVED           computed from the above (see calc.py)
  FIXTURE           value drawn in the H2-E/H2-E.1 fixture schematic (candA_fixture), unchanged
  CANDIDATE         value chosen for the A-IL12 candidate circuit in this study
  ASSUMED           engineering assumption with no datasheet backing (e.g. capacitor DC-bias derating)
  HYPOTHETICAL      sweep value for an unspecified parameter; never a device guarantee
"""
from collections import namedtuple

Q = namedtuple('Q', 'value tag src')
EF = 'TPS25947 SLVSFC9C'
P = {
    # ---------------- TPS259470LRPW eFuse (SLVSFC9C, May 2026) ----------------
    'ron_typ':      Q(28.3e-3, 'DS-TYP', f'{EF} 6.5, VIN 12 V, 3 A, 25 C'),
    'ron_max':      Q(45e-3, 'DS-MAX', f'{EF} 6.5, 2.7-23 V, -40..125 C'),
    'vuvp_r':       Q((2.44, 2.53, 2.64), 'DS-MIN/TYP/MAX', f'{EF} 6.5'),
    'vuvp_f':       Q((2.35, 2.42, 2.55), 'DS-MIN/TYP/MAX', f'{EF} 6.5'),
    'vuvlo_r':      Q((1.183, 1.20, 1.223), 'DS-MIN/TYP/MAX', f'{EF} 6.5 EN/UVLO'),
    'vuvlo_f':      Q((1.076, 1.09, 1.116), 'DS-MIN/TYP/MAX', f'{EF} 6.5 EN/UVLO'),
    'vov_r':        Q((1.183, 1.20, 1.223), 'DS-MIN/TYP/MAX', f'{EF} 6.5 OVLO'),
    'vov_f':        Q((1.076, 1.09, 1.116), 'DS-MIN/TYP/MAX', f'{EF} 6.5 OVLO'),
    'iovlkg':       Q(0.1e-6, 'DS-MAX', f'{EF} 6.5, only for 0.5 V < VOVLO < 1.5 V'),
    'ilim_6k65':    Q((0.425, 0.500, 0.575), 'DS-MIN/TYP/MAX', f'{EF} 6.5, RILM = 6.65 k'),
    'rilm_roc':     Q((549.0, 6650.0), 'DS-MIN/MAX', f'{EF} 6.3 RILM'),
    'isc_gain':     Q(2.01, 'DS-TYP', f'{EF} 6.5 ISCGain 201 % (no min/max)'),
    'ift':          Q(22.2, 'DS-TYP', f'{EF} 6.5 IFT (no min/max)'),
    't_ovlo':       Q(1.2e-6, 'DS-TYP', f'{EF} 6.6 tOVLO, VOVLO > VOV(R) to VOUT falling; NO MAX'),
    't_sc':         Q(0.5e-6, 'DS-TYP', f'{EF} 6.6 tSC (IOUT > 3 x ILIM) / tFT; NO MAX'),
    't_ft_deglitch': Q(30e-6, 'DS-TYP', f'{EF} 7.3.5.4 text "short de-glitch interval (30 us)"; no limit'),
    't_swov':       Q(90e-6, 'DS-TYP', f'{EF} 6.6 tSWOV OVLO fast recovery (non-latching); NO MIN'),
    't_rcb':        Q(1e-6, 'DS-TYP', f'{EF} 6.6 tRCB reverse-current comparator'),
    'idvdt':        Q((0.81e-6, 2.21e-6, 3.82e-6), 'DS-MIN/TYP/MAX', f'{EF} 6.5 IdVdt'),
    'sr_gain':      Q((0.709, 0.888, 1.018), 'DERIVED', f'{EF} 6.7 SRON x CdVdt / IdVdt(typ) at 2.7/12/23 V (typ table)'),
    'iq_on':        Q(610e-6, 'DS-MAX', f'{EF} 6.5 IQ(ON) TPS259470x'),
    'ioutlkg_ovlo': Q(443e-6, 'DS-MAX', f'{EF} 6.5 OUT leakage in OVLO, VOUT > VIN only'),
    'ipglkg':       Q(3e-6, 'DS-MAX', f'{EF} 6.5 AUXOFF leakage while asserted (high)'),
    'vaux_unpow':   Q((0.67, 1.0), 'DS-TYP/MAX', f'{EF} 6.5 VPGD: AUXOFF with VIN < UVP (26 uA / 242 uA)'),
    'absmax_in':    Q(28.0, 'DS-MAX', f'{EF} 6.1'),
    'sr_in_r':      Q(100e6, 'DS-MAX', f'{EF} 6.1 SRIN(R) 100 V/us'),
    'sr_in_f':      Q(10e6, 'DS-MAX', f'{EF} 6.1 SRIN(F) 10 V/us'),
    'absmax_pin':   Q(6.5, 'DS-MAX', f'{EF} 6.1 EN/UVLO, OVLO, AUXOFF, FLT'),
    'roc_en':       Q(5.0, 'DS-MAX', f'{EF} 6.3'),
    'roc_ovlo':     Q((0.5, 1.5), 'DS-MIN/MAX', f'{EF} 6.3 OVLO pin range'),
    'roc_aux':      Q(5.0, 'DS-MAX', f'{EF} 6.3 AUXOFF'),
    'roc_in':       Q((2.7, 23.0), 'DS-MIN/MAX', f'{EF} 6.3'),
    'dvdt_rating':  Q(5.0, 'DS-MIN', f'{EF} 6.3 dVdt capacitor rating >= VIN + 5 V'),
    # ---------------- TPS7A2550 U1 (SBVS372C) ----------------
    'vldo':         Q((4.92, 5.00, 5.08), 'DERIVED', 'SBVS372C p6 +-1 %, line 0.1 %, load 0.5 % (same as H2-D budget)'),
    'icl_ldo':      Q((0.325, 0.510, 0.720), 'DS-MIN/TYP/MAX', 'SBVS372C 6.5 ICL'),
    'vdo_ldo':      Q(0.340, 'DS-MAX', 'SBVS372C 6.5 dropout at 300 mA'),
    'cout_ldo':     Q((1e-6, 2.2e-6, 100e-6), 'DS-MIN/TYP/MAX', 'SBVS372C 6.3 COUT; TI note: values assume 50 % derating'),
    'v_fault':      Q((12.0, 13.2), 'ASSUMED', 'VIN_12V nominal and +10 % (same convention as H2-E.1)'),
    # ---------------- TPS3703A7330 U3 on +5V_IL (SBVS249B) ----------------
    'u3_uv':        Q((4.603, 4.644, 4.693), 'DERIVED', 'h2e1_checks.py window(): A7330, 5.49k/10.7k 0.1 %'),
    'u3_ov':        Q((5.296, 5.343, 5.399), 'DERIVED', 'h2e1_checks.py window()'),
    'u3_hys':       Q((0.003, 0.008), 'DS-MIN/MAX', 'SBVS249B 7.5 VHYS'),
    'tpd_3703':     Q(30e-6, 'DS-MAX', 'SBVS249B 7.6 tPD at 5 % overdrive'),
    'td_3703':      Q((0.140, 0.200, 0.260), 'DS-MIN/TYP/MAX', 'SBVS249B 7.6 tD, CT = 10 k to VDD'),
    'tpd_mr':       Q(0.5e-6, 'DS-TYP', 'SBVS249B 7.6 tPD(MR); NO MAX'),
    'vmr_l':        Q(0.3, 'DS-MAX', 'SBVS249B 7.5 VMR_L'),
    'vmr_h':        Q(1.4, 'DS-MIN', 'SBVS249B 7.5 VMR_H'),
    'rmr':          Q(100e3, 'DS-TYP', 'SBVS249B 7.5 RMR internal pull-up'),
    'u3_uvlo':      Q((1.2, 1.7), 'DS-MIN/MAX', 'SBVS249B 7.5; RESET driven low below UVLO'),
    'vol_3703':     Q((0.25, 5e-3), 'DS-MAX', 'SBVS249B 7.5 VOL <= 0.25 V at 5 mA, VDD = 5 V (3 mA at VDD = 2 V)'),
    'absmax_3703':  Q(6.0, 'DS-MAX', 'SBVS249B 7.1 VDD, SENSE, MR, RESET'),
    'roc_3703':     Q(5.5, 'DS-MAX', 'SBVS249B 7.3'),
    # ---------------- other +5V_IL / VCB consumers ----------------
    'absmax_tlv320x': Q(7.0, 'DS-MAX', 'SBOS561C 6.1 supply'), 'roc_tlv320x': Q(5.5, 'DS-MAX', 'SBOS561C 6.3'),
    'tpd_tlv320x':  Q(55e-9, 'DS-MAX', 'SBOS561C (as H2-D budget)'),
    'absmax_3430':  Q(7.0, 'DS-MAX', 'SBVS366A VDD'), 'roc_3430': Q(6.5, 'DS-MAX', 'SBVS366A'),
    'absmax_lvc':   Q(6.5, 'DS-MAX', 'SCES351Y VCC (U13 on VCB)'), 'roc_lvc': Q(5.5, 'DS-MAX', 'SCES351Y'),
    # ---------------- TPS16630 U10 (SLVSET9G) ----------------
    'v_shutf':      Q(0.8, 'DS-MIN', 'SLVSET9G 6.5 V(SHUTF) falling (single limit)'),
    'v_shutr':      Q(2.0, 'DS-MAX', 'SLVSET9G 6.5 V(SHUTR) rising'),
    'i_shdn':       Q(10e-6, 'DS-MAX', 'SLVSET9G 6.5 I(SHDN) source at 0 V'),
    'tsd_1663':     Q(1.5e-6, 'DS-MAX', 'SLVSET9G p10 SHDN to FET OFF (H2-D budget)'),
    'u10_uvlo_off': Q(3.88, 'DERIVED', 'FIXTURE_DESIGN 1.3: FET can be on only above +5V_IL = 3.88 V'),
    # ---------------- discrete MOSFETs ----------------
    'n7002_vth':    Q((1.0, 2.5), 'DS-MIN/MAX', 'onsemi 2N7002L-D Rev. ON char., 25 C'),
    'n7002_rds':    Q((7.5, 13.5), 'DS-MAX', 'onsemi 2N7002L-D, VGS 5 V, 50 mA, 25 / 125 C'),
    'n7002_ciss':   Q(50e-12, 'DS-MAX', 'onsemi 2N7002L-D Ciss'),
    'bss84_vth':    Q((-2.0, -0.9), 'DS-MIN/MAX', 'onsemi BSS84LT1/D Rev. 23, 25 C (VGS(th) magnitude 0.9..2.0 V)'),
    'bss84_rds':    Q(10.0, 'DS-MAX', 'onsemi BSS84LT1/D, VGS -5 V, -100 mA, 25 C'),
    # ---------------- zener named in the proposal ----------------
    'bzx84_lowest': Q(2.4, 'DS', 'Diodes DS18001 / onsemi BZX84C2V4LT1/D: series starts at 2V4; no 1V5 type'),
    'bzx84c2v4_ir': Q((50e-6, 1.0), 'DS-MAX', 'Diodes DS18001: IR 50 uA at VR 1.0 V'),
    # ---------------- fixture values (unchanged) ----------------
    'r2_pu':        Q(2.2e3, 'FIXTURE', 'R2 P pull-up'), 'c11_p': Q(100e-12, 'FIXTURE', 'C11'),
    'r52': Q(47e3, 'FIXTURE', 'R52'), 'r53': Q(47e3, 'FIXTURE', 'R53'), 'c25': Q(1e-9, 'FIXTURE', 'C25 C0G'),
    'r_sd':         Q(10.0, 'ASSUMED', 'Q_sd on-resistance PLACEHOLDER, as H2-D budget'),
    'r1_vcb':       Q(100.0, 'FIXTURE', 'R1'), 'c5_vcb': Q(10e-6, 'FIXTURE', 'C5 10 uF 10 V X7R 1206'),
    'i_vcb':        Q(1.5e-3, 'DERIVED', 'H2-D budget VCB load (100 ohm x 1.5 mA)'),
    'cd_k':         Q(0.8, 'FIXTURE', 'R50/R51 2.55k/10.2k: CD trips at P < 0.8 VCB'),
    'tail_us':      Q(16.5, 'DERIVED', 'H2-D budget.py: P sink asserted -> drain < 0.5 V (P_FALL + CD + crowbar + discharge)'),
    'r4_limit_us':  Q(50.0, 'DS', 'R4 requirement: drain < 0.5 V within 50 us of fault onset (H2-C/H2-D)'),
    # ---------------- capacitor DC-bias (no datasheet curve was read) ----------------
    'dcb_47u_1210_16v': Q((0.55, 0.75), 'ASSUMED', 'retained C at 5 V; GRM32ER61C476ME15 curve NOT read'),
    'dcb_4u7_0603_10v': Q((0.40, 0.60), 'ASSUMED', 'retained C at 5 V; CL10A475KP8NNNC curve NOT read'),
    'dcb_4u7_0805_25v': Q((0.55, 0.80), 'ASSUMED', 'retained C at 5 V; CL21A475KAQNNNE curve NOT read'),
    'dcb_1u_0603_25v_hv': Q((0.35, 0.60), 'ASSUMED', 'retained C at 13 V; CL10B105KA8NNNC curve NOT read'),
    'dcb_100n_0402':    Q((0.80, 0.95), 'ASSUMED', 'retained C at 5 V, 16 V X7R'),
    'x5r_temp':     Q(0.15, 'DS', 'EIA X5R/X7R: +-15 % over temperature'),
    'i_il':         Q((3e-3, 6e-3, 15e-3), 'ASSUMED', '+5V_IL static load excl. R2, R1/VCB and the new interface; not inventoried'),
}


def v(name, i=None):
    val = P[name].value
    return val if i is None else val[i]
