#!/usr/bin/env python3
"""H2-C power sequencing / PA-drain interlock simulation runner -- BEHAVIOURAL / PRELIMINARY, not hardware-validated.

Usage:  env -u LD_LIBRARY_PATH python3 run_h2c_sim.py [--quick]      (--quick: 60 ordering runs instead of 920)
Writes: h2c_results.md, h2c_*.png, d_worst_*.cir. Exit 1 if any SAFETY check fails for a GATING design
(the recommended design "REC", nominal and pessimistic logic). Non-gating designs (the current schematic "R2" and the
alternatives) are simulated with the same checks and reported -- their failures are shown, never hidden.

Safety criteria (project lead, revision 2):
  G    VGG_PA within -2.0 V .. 0 V at all times, ADAR1000 powered or not. H2-E correction: the former +10 mV allowance above the
       0 V abs max had no manufacturer basis and is removed; the recorded H2-C/D results (+2 mV) therefore FAIL criterion G
  A    drain (VOUT) < 0.5 V whenever any gate > -1.5 V outside armed TX (and outside the 50 us after a fault / stop)
  T50  drain < 0.5 V within 50 us of any interlock fault (HARD criterion)
  (a)  TPS22810 switch open (tOFF complete) <= 10 us after the fault crosses its threshold
  (b)  residual drain energy into the PAs after the switch opens <= 0.25 mJ per chain, peak PA current <= 0.6 A (+1 %)
  EN   no drain switch on while any supply is invalid (> 10 us after the supply leaves its window)
  REF  no gate reference (IL_REF > 0.3 V) while any supply is invalid (> 50 us after it leaves its window)
"""
import os, sys, subprocess, tempfile, re, itertools, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
VECS = ("vin aux v18 v3rf v5pa vneg n5v n3v3 pg_3v3rf enn neg_rails_ok il_ref gates_ok gates_pinched neg_ok "
        "il_en sw_en_d mcu_pa_en wdt_ok il_clr_n pa_armed pa_drain_en vout gate1 gate2 gate3 gate4 ipa1 ipa2 ipa3 ipa4 "
        "icb cbg ilsrc supvdd isup pg_tsink sup_act il_q3g").split()
VDRAIN, VGATE, GRACE = 0.5, -1.5, 50e-6
T_REACT, E_MAX, I_MAX, VG_HI, VG_LO = 10e-6, 0.25e-3, 0.6 * 1.01, 0.0, -2.0  # H2-E: no allowance above the 0 V abs max
VIL = 0.35 * 1.65  # LVC VIL at VCC 1.65 V (SCES794G p6)
ms = 1e-3
TD_SW = 130.7e-6   # TPS22810 tD (model) -- VOUT starts rising this long after the switch enable

ASB = dict(cb_en=1, ilref_mode=2, sup_en=1, rf_uv=3.1, cref="10n", asb=1,          # as built (IMPL_REC / REC_PARTS)
           cb_r=0.362, cb_vth=1.1, cb_ciss="340p",                               # CSD16301Q2 29 mohm max + 3x1 ohm
           q2_vth=0.75, sup_vth=1.6706, sup_aux=2.968, sup_trst=9.6, sup_tdet="0.1u")
DESIGNS = {  # name: (plant .param overrides, description, gating)
    "R2":  ({}, "schematic before REC (rev 2: U915 only)", False),
    "ASB": (ASB, "as built: REC with CSD16301Q2 / 3x1 ohm / DMG1012T Q2,Q3,Q966 / TPS386000 / BAT54C / TLV75518P", True),
    "ASB_cb09":  ({**ASB, "cb_vth": 0.9}, "as built, crowbar VGS(th) 0.9 V (min)", True),
    "ASB_cb155": ({**ASB, "cb_vth": 1.55}, "as built, crowbar VGS(th) 1.55 V (max)", True),
    "ASB_q05":   ({**ASB, "q2_vth": 0.5}, "as built, DMG1012T VGS(th) 0.5 V (Q2, Q3, Q966)", True),
    "ASB_q10":   ({**ASB, "q2_vth": 1.0}, "as built, DMG1012T VGS(th) 1.0 V (Q2, Q3, Q966)", True),
    "ASB_toff-": ({**ASB, "tsw_off": "1.65u"}, "as built, TPS22810 tOFF -50 % (1.65 us)", True),
    "ASB_toff+": ({**ASB, "tsw_off": "4.95u"}, "as built, TPS22810 tOFF +50 % (4.95 us)", True),
    "ASB_td20":  ({**ASB, "sup_tdet": "20u"}, "as built, supervisor detection delay 20 us", True),
    "ASB_td50":  ({**ASB, "sup_tdet": "50u"}, "as built, supervisor detection delay 50 us", True),
    "ASB_td100": ({**ASB, "sup_tdet": "100u"}, "as built, supervisor detection delay 100 us", True),
    "ASB_slow":  ({**ASB, "q2_vth": 0.5, "cb_vth": 1.55, "sup_tdet": "100u"},
                  "as built, slow-crowbar corner: Q2 0.5 V, crowbar 1.55 V, supervisor 100 us", True),
    "ASB_ovl":   ({**ASB, "q2_vth": 1.0, "cb_vth": 0.9, "tsw_off": "4.95u"},
                  "as built, overlap corner: Q2 1.0 V, crowbar 0.9 V, tOFF +50 %", True),
    "FIX":       ({**ASB, "fetclamp": 1},
                  "candidate M5 fix (not built): BAT54C clamps replaced by 2 x DMG1012T on IL_Q3G; R976 fed from supervisor VDD OR +1V8_DIG", False),
    "FIX_slow":  ({**ASB, "fetclamp": 1, "q2_vth": 0.5, "cb_vth": 1.55, "sup_tdet": "100u"}, "FIX at the slow corner", False),
    "FIX_ovl":   ({**ASB, "fetclamp": 1, "q2_vth": 1.0, "cb_vth": 0.9, "tsw_off": "4.95u"}, "FIX at the overlap corner", False),
}
MODES = {"nom": {}, "pess": dict(pess=1)}


def with_params(cir_text, params):
    """Insert a .param override line after the plant include (later .param wins in ngspice; derived params follow)."""
    if not params:
        return cir_text
    line = ".param " + " ".join(f"{k}={v}" for k, v in params.items())
    assert ".include h2c_plant.inc" in cir_text
    return cir_text.replace(".include h2c_plant.inc", ".include h2c_plant.inc\n" + line, 1)


def ngrun(cir, out):
    subprocess.run([sys.executable, os.path.join(HERE, "ngrun.py"), cir, out, *VECS], cwd=HERE, check=True,
                   env={k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = np.loadtxt(out)
    s = {k: d[:, 2 * i + 1] for i, k in enumerate(VECS)}
    s["t"] = d[:, 0]
    s["gmax"] = np.max([s[f"gate{k}"] for k in range(1, 5)], axis=0)
    s["gmin"] = np.min([s[f"gate{k}"] for k in range(1, 5)], axis=0)
    s["ipa"] = s["ipa1"] + s["ipa2"] + s["ipa3"] + s["ipa4"]
    return s


def run_variant(cir_text, params, tmp, tag):
    cir = os.path.join(tmp, f"{tag}.cir")
    open(cir, "w").write(with_params(cir_text, params).replace(".include h2c_plant.inc",
                                                                f".include {HERE}/h2c_plant.inc"))
    return ngrun(cir, os.path.join(tmp, f"{tag}.dat"))


def cross(s, sig, thr, rise=True, t0=0.0):
    """First crossing time of s[sig] through thr after t0 (linear interpolation); None if never."""
    t, y = s["t"], s[sig] if isinstance(sig, str) else sig
    m = t >= t0
    tt, yy = t[m], y[m]
    if not len(tt):
        return None
    above = yy > thr if rise else yy < thr
    if above[0]:
        return tt[0]
    idx = np.nonzero(above)[0]
    if not len(idx):
        return None
    i = idx[0]
    return tt[i - 1] + (thr - yy[i - 1]) * (tt[i] - tt[i - 1]) / (yy[i] - yy[i - 1])


def at(s, sig, t):
    return float(np.interp(t, s["t"], s[sig]))


def fmt(t):
    return "never" if t is None else f"{t / ms:.4f} ms"


def dt_us(a, b):
    return "n/a" if a is None or b is None else f"{(a - b) * 1e6:+.1f} us"


def fmtu(x):
    return "n/a" if x is None else f"{x:.1f} us"


def energy(s, sig, t0, t1):
    m = (s["t"] >= t0) & (s["t"] <= t1)
    return float(np.trapz(s["vout"][m] * s[sig][m], s["t"][m])) if m.sum() > 1 else 0.0


def supplies_valid(s):
    """Supply windows = the hardware monitor thresholds (ratiometric to +1V8_DIG, INTERLOCK_SPEC 3.4), so that the
    fault time is the comparator trip itself (including the model's 0.5 mV offset): -5V_BF -4.60 V, -3V3_SW -3.00 V, +3V3_AUX 2.97 V at +1V8_DIG = 1.8 V;
    plus +1V8_DIG >= 1.65 V (LVC VCC min) and +3V3_RF >= 85 % (PGOOD)."""
    v18 = s["v18"]
    a, b = 49.9 / 62.3, 12.4 / 62.3                       # rail divider weights (R949 / R948)
    vio = 0.5e-3                                           # model comparator offset (late-trip direction)
    n5_th = (v18 * 1.62 / 5.54 + vio - a * v18) / b
    n3_th = (v18 * 1.07 / 2.28 + vio - a * v18) / b
    aux_th = (v18 * 1.62 / 5.54 - vio) * 56.4 / 10.0
    return ((s["aux"] >= aux_th) & (v18 >= 1.65) & (s["v3rf"] >= 0.85 * 3.327) & (s["n5v"] <= n5_th)
            & (s["n3v3"] <= n3_th))


def onsets(mask, t):
    """Times where mask goes False -> True (and t[0] if it starts True)."""
    e = np.nonzero(mask[1:] & ~mask[:-1])[0] + 1
    return ([t[0]] if mask[0] else []) + list(t[e])


def grace_mask(t, starts, width):
    g = np.zeros_like(t, bool)
    for a in starts:
        g |= (t >= a) & (t < a + width)
    return g


def crowbar_metrics(s):
    """Shoot-through and break-before-make margins of the drain crowbar (empty if no crowbar current)."""
    t = s["t"]
    if s["icb"].max() < 1e-3:
        return {}
    on_cb = s["icb"] > 0.05
    ovl = on_cb & (s["sw_en_d"] > 0.5)
    m_off, m_on = [], []
    for te in onsets(s["sw_en_d"] < 0.5, t):          # switch opens -> crowbar may start
        tc = cross(s, s["icb"], 0.05, True, te)
        if tc is not None and at(s, "vout", te) > 0.5:
            m_off.append(tc - te)
    for te in onsets(s["sw_en_d"] > 0.5, t):          # switch enable -> crowbar must be off before tD
        tq = cross(s, s["cbg"], 0.9, False, te)
        if te > t[0]:
            m_on.append(TD_SW - ((tq - te) if tq is not None else 1.0))
    return dict(i_pk=float(s["icb"].max()), e_cb=energy(s, "icb", t[0], t[-1]),
                overlap_us=float(np.sum(np.diff(t)[ovl[:-1]])) * 1e6,
                bbm_off_us=min(m_off) * 1e6 if m_off else None, bbm_on_us=min(m_on) * 1e6 if m_on else None)


def check_safety(s, tx, faults, rearm):
    """Generic checks. tx: allowed armed-TX windows; faults: [(label, t_fault)]; rearm: legit re-arm times.
    Returns (checks, metrics): checks = (name, ok, detail, 'safety'|'info')."""
    t = s["t"]
    res, met = [], []
    allowed = np.zeros_like(t, bool)
    for a, b in tx:
        allowed |= (t >= a) & (t < b)
    allowed |= grace_mask(t, [tf for _, tf in faults if tf is not None], GRACE)
    for label, tf in faults:
        if tf is None:
            res.append((f"fault '{label}' never reached", False, "scenario did not develop", "safety"))
            continue
        t_open = cross(s, "sw_en_d", 0.5, False, tf)
        t05 = cross(s, "vout", VDRAIN, rise=False, t0=tf)
        tend = min([r for r in rearm if r > tf], default=t[-1])
        react = None if t_open is None else t_open - tf
        e = energy(s, "ipa", t_open, tend) if t_open is not None else float("nan")
        w = (t >= tf) & (t < tend)
        ipk = max(s[f"ipa{k}"][w].max() for k in range(1, 5))
        ok50 = at(s, "vout", tf + GRACE) < VDRAIN
        tg15 = cross(s, "gmax", -0.15, t0=tf + 1e-9) if s["gmax"][t >= tf][0] < -0.15 else None
        tg0 = cross(s, "gmax", -0.01, t0=tf + 1e-9)
        res.append((f"T50: drain < 0.5 V within 50 us of '{label}'", ok50,
                    f"VOUT < 0.5 V at {dt_us(t05, tf)}; VOUT at +50 us = {at(s, 'vout', tf + GRACE):.2f} V", "safety"))
        res.append((f"(a) switch open <= 10 us after '{label}'", react is not None and react <= T_REACT,
                    f"tOFF complete {dt_us(t_open, tf)}", "safety"))
        res.append((f"(b) residual PA energy <= 0.25 mJ, peak PA current <= 0.6 A after '{label}'",
                    e <= E_MAX and ipk <= I_MAX, f"E = {e * 1e3:.3f} mJ; peak per-PA {ipk:.3f} A", "safety"))
        res.append((f"INFO gate vs drain after '{label}'", True,
                    f"drain < 0.5 V at {dt_us(t05, tf)}; first gate > -0.15 V at {dt_us(tg15, tf)}; "
                    f"> 0 V at {dt_us(tg0, tf)}", "info"))
        met.append(dict(label=label, react=react, e=e, ipk=ipk, t05=None if t05 is None else t05 - tf,
                        tg15=None if tg15 is None else tg15 - tf))
    bad = (s["vout"] > VDRAIN) & (s["gmax"] > VGATE) & ~allowed
    res.insert(0, ("A: drain < 0.5 V whenever a gate > -1.5 V outside armed TX", not bad.any(),
                   "ok" if not bad.any() else
                   f"violated {t[bad][0] / ms:.4f}..{t[bad][-1] / ms:.4f} ms, max VOUT {s['vout'][bad].max():.2f} V",
                   "safety"))
    res.insert(0, ("G: VGG_PA within -2.0 .. 0 V", s["gmax"].max() <= VG_HI and s["gmin"].min() >= VG_LO,
                   f"max {s['gmax'].max() * 1e3:+.0f} mV at {t[np.argmax(s['gmax'])] / ms:.3f} ms, "
                   f"min {s['gmin'].min():.3f} V", "safety"))
    inval = ~supplies_valid(s)
    on_bad = (s["sw_en_d"] > 0.5) & inval & ~grace_mask(t, onsets(inval, t), T_REACT)
    ref_bad = (s["il_ref"] > 0.3) & inval & ~grace_mask(t, onsets(inval, t), GRACE)
    res.append(("EN: drain switch never on while a supply is invalid", not on_bad.any(),
                "ok" if not on_bad.any() else f"on while invalid {t[on_bad][0] / ms:.4f}..{t[on_bad][-1] / ms:.4f} ms",
                "safety"))
    res.append(("REF: IL_REF never on while a supply is invalid", not ref_bad.any(),
                "ok" if not ref_bad.any() else
                f"IL_REF up to {s['il_ref'][ref_bad].max():.2f} V while invalid, {t[ref_bad][0] / ms:.4f}.."
                f"{t[ref_bad][-1] / ms:.4f} ms", "safety"))
    if s["isup"].max() > 0 or s["pg_tsink"].max() > 0.5:     # as-built PG_3V3RF sink / BAT54C clamp checks (M5)
        asrt = (s["pg_tsink"] > 0.5) | (s["sup_act"] > 0.5)
        m = asrt & ~grace_mask(t, onsets(asrt, t), 2e-6)
        live = s["v18"] >= 1.0                                   # LVC drivers able to push clamp current
        pgx = s["pg_3v3rf"][m].max() if m.any() else 0.0
        pdx = s["pa_drain_en"][m].max() if m.any() else 0.0
        vv = m & (s["v18"] >= 1.65)
        clr = (s["il_clr_n"][vv] - 0.35 * s["v18"][vv]).max() if vv.any() else -1.0
        isx = s["isup"].max()
        res.append(("M5a: PG_3V3RF <= 0.3 V whenever asserted (TLV755 EN guaranteed off)", pgx <= 0.3,
                    f"max {pgx:.3f} V", "safety"))
        res.append(("M5b: clamped PA_DRAIN_EN < VENF min 1.08 V while PG_3V3RF asserted", pdx < 1.08,
                    f"max {pdx:.3f} V", "safety"))
        res.append(("M5c: clamped IL_CLR_N < LVC VIL (0.35 VCC) while PG_3V3RF asserted, VCC valid", clr < 0,
                    f"max margin {clr * 1e3:+.0f} mV", "safety"))
        res.append(("M5d: TPS386000 RESET_N sink current <= 5 mA abs max", isx <= 5e-3,
                    f"max {isx * 1e3:.2f} mA (VOL specified only at 1 mA)", "safety"))
        met5 = dict(pg=pgx, pd=pdx, clr=clr, isup=isx, live=bool(live.any()))
    else:
        met5 = None
    cb = crowbar_metrics(s)
    if cb:
        res.append(("CB: no crowbar / switch overlap (shoot-through)", cb["overlap_us"] < 0.01,
                    f"overlap {cb['overlap_us']:.2f} us; crowbar starts {fmtu(cb['bbm_off_us'])} after switch opens; "
                    f"crowbar off {fmtu(cb['bbm_on_us'])} before VOUT ramp; peak {cb['i_pk']:.1f} A, "
                    f"{cb['e_cb'] * 1e3:.3f} mJ total", "safety"))
    if cb is not None:
        cb = dict(cb, m5=met5) if cb else ({"m5": met5} if met5 else {})
    return res, met, cb


# ----------------------------------------------------------------------------- scenarios
def s1(s):
    ev = [("VIN_12V > 8 V (TPS62933 UVLO start)", cross(s, "vin", 8)),
          ("+3V3_AUX > 3.0 V", cross(s, "aux", 3.0)),
          ("+1V8_DIG > 1.71 V", cross(s, "v18", 1.71)),
          ("PWR_EN_3V3 / 5VPA / NEG asserted (MCU)", 8.001 * ms),
          ("+3V3_RF (AVDD3, VDD_SW) > 90 %", cross(s, "v3rf", 0.9 * 3.327)),
          ("+5V_PA > 4.5 V", cross(s, "v5pa", 4.5)),
          ("PG_3V3RF high", cross(s, "pg_3v3rf", 0.9)),
          ("ENN (U913) high", cross(s, "enn", 0.9)),
          ("PWR_VNEG < -6.0 V", cross(s, "vneg", -6.0, False)),
          ("-3V3_SW (VSS_SW) < -0.33 V", cross(s, "n3v3", -0.33, False)),
          ("-5V_BF (AVDD1) < -0.5 V", cross(s, "n5v", -0.5, False)),
          ("-3V3_SW < -3.0 V (monitor trip)", cross(s, "n3v3", -3.0, False)),
          ("-5V_BF < -4.6 V (monitor trip)", cross(s, "n5v", -4.6, False)),
          ("NEG_RAILS_OK > 0.675 V first time (glitch: LM339 below VS min 2 V)", cross(s, "neg_rails_ok", 0.675)),
          ("IL_EN high first time (U915)", cross(s, "il_en", 0.9)),
          ("IL_REF > 0.5 V first time", cross(s, "il_ref", 0.5)),
          ("+3V3_AUX > 2.0 V (LM339 active, glitch ends)", cross(s, "aux", 2.0)),
          ("NEG_RAILS_OK high (rails good)", cross(s, "neg_rails_ok", 0.9, t0=100 * ms)),
          ("IL_REF > 1.7 V (rails good)", cross(s, "il_ref", 1.7, t0=100 * ms)),
          ("firmware PA_BIAS -> -1.75 V", 140.0 * ms),
          ("all gates < -1.5 V", cross(s, "gmax", -1.5, False, 139.9 * ms)),
          ("GATES_OK high", cross(s, "gates_ok", 0.9, t0=139.9 * ms)),
          ("GATES_PINCHED high", cross(s, "gates_pinched", 0.9, t0=139.9 * ms)),
          ("NEG_OK high first time", cross(s, "neg_ok", 0.9)),
          ("PA_ARMED high first time (pessimistic flop SET while +1V8_DIG < 1.65 V)", cross(s, "pa_armed", 0.5)),
          ("PA_DRAIN_EN > 1.08 V first time", cross(s, "pa_drain_en", 1.08)),
          ("NEG_OK high (gates pinched)", cross(s, "neg_ok", 0.9, t0=100 * ms)),
          ("MCU_PA_EN high", cross(s, "mcu_pa_en", 0.9, t0=100 * ms)),
          ("PA_ARMED high", cross(s, "pa_armed", 0.9, t0=100 * ms)),
          ("PA_DRAIN_EN high", cross(s, "pa_drain_en", 0.9, t0=100 * ms)),
          ("VOUT (drain) > 0.5 V", cross(s, "vout", 0.5, t0=100 * ms)),
          ("VOUT (drain) > 4.5 V", cross(s, "vout", 4.5, t0=100 * ms)),
          ("firmware PA_BIAS -> -1.1 V (TX)", 141.0 * ms),
          ("any gate > -1.5 V", cross(s, "gmax", -1.5, t0=140.5 * ms))]
    d = dict(ev)
    t_avdd3 = d["+3V3_RF (AVDD3, VDD_SW) > 90 %"]
    chk = [("AVDD3 (+3V3_RF 90 %) before AVDD1 (-5V_BF -10 %) [ADAR1000 p13]",
            t_avdd3 < d["-5V_BF (AVDD1) < -0.5 V"], f"lead {(d['-5V_BF (AVDD1) < -0.5 V'] - t_avdd3) / ms:.2f} ms"),
           ("VDD_SW (+3V3_RF 90 %) before VSS_SW (-3V3_SW -10 %) [ADTR1107 p24]",
            t_avdd3 < d["-3V3_SW (VSS_SW) < -0.33 V"], f"lead {(d['-3V3_SW (VSS_SW) < -0.33 V'] - t_avdd3) / ms:.2f} ms"),
           ("TPS65131 does not start (PWR_VNEG < -0.5 V) before PG_3V3RF, although PWR_EN_NEG was asserted early",
            (cross(s, "vneg", -0.5, False) or 1) >= d["PG_3V3RF high"] - 1e-6,
            f"PWR_VNEG < -0.5 V at {fmt(cross(s, 'vneg', -0.5, False))}, PG at {fmt(d['PG_3V3RF high'])}"),
           ("INFO: ENN logic level not high before PG_3V3RF (U913 output; pessimistic mode drives it to VCC while "
            "+1V8_DIG < 1.65 V)", (cross(s, "enn", 0.9) or 1) >= d["PG_3V3RF high"] - 1e-6,
            f"ENN first high at {fmt(cross(s, 'enn', 0.9))}", "info"),
           ("PA_ARMED only after all gates pinched",
            d["PA_ARMED high"] > d["all gates < -1.5 V"], dt_us(d["PA_ARMED high"], d["all gates < -1.5 V"]))]
    gpos = s["gmax"][s["t"] < 139.9 * ms].max()
    notes = [f"max IL_REF before -5V_BF is good: {s['il_ref'][s['t'] < 100 * ms].max():.3f} V; max NEG_OK: "
             f"{s['neg_ok'][s['t'] < 100 * ms].max():.3f} V; max NEG_RAILS_OK during AUX ramp "
             f"{s['neg_rails_ok'][s['t'] < 5 * ms].max():.3f} V (unchanged pull-up, now gated by PG_3V3RF in U915)",
             f"max gate voltage before firmware programs PA_BIAS: {gpos * 1e3:+.1f} mV (ADAR1000 unpowered/at reset)",
             "-3V3_SW and -5V_BF ramp together (same TPS65131, same 120 ms SS); ADAR1000 p44 lists -3.3 V before -5 V: "
             f"-3V3_SW reaches -10 % {dt_us(d['-5V_BF (AVDD1) < -0.5 V'], d['-3V3_SW (VSS_SW) < -0.33 V'])} before -5V_BF",
             f"TX drain current (4 PAs) at end: {s['ipa'][-1]:.3f} A, VOUT {s['vout'][-1]:.2f} V"]
    return ev, chk, [(141.0 * ms, 1)], [], [], notes


def s2(s):
    ev = [("NEG_RAILS_OK high", cross(s, "neg_rails_ok", 0.9)),
          ("MCU_PA_EN high (gates at reset 0 V)", 140.2 * ms),
          ("MCU_PA_EN low", 140.5 * ms),
          ("gates programmed ON -1.1 V (not pinched)", 140.6 * ms),
          ("MCU_PA_EN high again", 140.7 * ms),
          ("PA_ARMED high", cross(s, "pa_armed", 0.9)),
          ("PA_DRAIN_EN high", cross(s, "pa_drain_en", 0.9)),
          ("VOUT > 0.5 V", cross(s, "vout", 0.5))]
    notes = [f"GATES_OK at 140.3 ms = {at(s, 'gates_ok', 140.3 * ms):.2f} V, NEG_OK = {at(s, 'neg_ok', 140.3 * ms):.2f} V, "
             f"IL_CLR_N = {at(s, 'il_clr_n', 140.3 * ms):.2f} V",
             f"GATES_PINCHED at 140.8 ms = {at(s, 'gates_pinched', 140.8 * ms):.2f} V, NEG_OK = {at(s, 'neg_ok', 140.8 * ms):.2f} V",
             f"max VOUT {s['vout'].max():.3f} V, max PA_ARMED {s['pa_armed'].max():.2f} V"]
    return ev, [], [], [], [], notes


def s3(s):
    t0 = 142.0 * ms
    tf = cross(s, "gate1", -0.15, t0=t0)
    t05 = cross(s, "vout", 0.5, False, t0)
    ev = [("PA_BIAS1 step -1.1 -> 0 V", t0),
          ("gate1 > -0.15 V (fault)", tf),
          ("GATES_OK low (< VIL)", cross(s, "gates_ok", VIL, False, t0)),
          ("NEG_OK low", cross(s, "neg_ok", 0.9, False, t0)),
          ("PA_ARMED low", cross(s, "pa_armed", 0.9, False, t0)),
          ("PA_DRAIN_EN low", cross(s, "pa_drain_en", 0.9, False, t0)),
          ("VOUT < 4.5 V", cross(s, "vout", 4.5, False, t0)),
          ("VOUT < 0.5 V", t05),
          ("PA_BIAS1 restored -1.1 V (must stay off)", 142.3 * ms)]
    m = s["t"] >= t0
    notes = [f"peak PA1 current {s['ipa1'][m].max():.3f} A (nominal 0.22 A); peak chain current {s['ipa'][m].max():.3f} A",
             f"PA1 energy from step to VOUT < 0.5 V: {energy(s, 'ipa1', t0, t05) * 1e3:.3f} mJ; "
             f"to sim end: {energy(s, 'ipa1', t0, s['t'][-1]) * 1e3:.3f} mJ; "
             f"stored in 19.81 uF at 5 V: {0.5 * 19.81e-6 * 25 * 1e3:.3f} mJ",
             f"VOUT at 142.5 ms after gate restored: {at(s, 'vout', 142.5 * ms):.3f} V, PA_ARMED {at(s, 'pa_armed', 142.5 * ms):.2f} V"]
    return ev, [], [(141.0 * ms, tf)], [("gate1 lost (> -0.15 V)", tf)], [], notes


def s4(s, label):
    t0 = 142.0 * ms
    tf = cross(s, "n5v", -4.6, t0=t0)
    tg = cross(s, "gmax", -0.15, t0=t0)
    ev = [(label, t0),
          ("PWR_VNEG > -5.2 V (LDO in dropout)", cross(s, "vneg", -5.2, t0=t0)),
          ("-5V_BF > -4.6 V (rail comparator)", tf),
          ("NEG_RAILS_OK low (< VIL)", cross(s, "neg_rails_ok", VIL, False, t0)),
          ("PA_DRAIN_EN low", cross(s, "pa_drain_en", 0.9, False, t0)),
          ("IL_REF < 0.1 V", cross(s, "il_ref", 0.1, False, t0)),
          ("VOUT < 0.5 V", cross(s, "vout", 0.5, False, t0)),
          ("any gate > -1.0 V (drifting above TX bias)", cross(s, "gmax", -1.0, t0=t0)),
          ("any gate > -0.15 V (gate-lost level)", tg),
          ("any gate > -0.01 V", cross(s, "gmax", -0.01, t0=t0))]
    d = dict(ev)
    first = "rail comparator (-4.6 V)" if tg is None or tf < tg else "gate-lost (-0.15 V)"
    notes = [f"first trip: {first}; drain < 0.5 V {dt_us(tg, d['VOUT < 0.5 V'])} before the first gate reaches -0.15 V"]
    return ev, [], [(141.0 * ms, tf)], [("-5V_BF > -4.6 V", tf)], [], notes


def s5a(s):
    t0 = 142.0 * ms
    ev = [("WDT_OK low", t0),
          ("PA_DRAIN_EN low", cross(s, "pa_drain_en", 0.9, False, t0)),
          ("PA_ARMED low", cross(s, "pa_armed", 0.9, False, t0)),
          ("VOUT < 0.5 V", cross(s, "vout", 0.5, False, t0)),
          ("WDT_OK high again", 142.5 * ms),
          ("MCU_PA_EN toggle with gates ON (142.6/142.7 ms)", 142.7 * ms),
          ("PA_ARMED high (should be after 143.0 ms)", cross(s, "pa_armed", 0.9, t0=142.55 * ms)),
          ("gates OFF -1.75 V", 142.8 * ms),
          ("MCU_PA_EN re-arm edge", 143.0 * ms),
          ("PA_DRAIN_EN high", cross(s, "pa_drain_en", 0.9, t0=142.55 * ms)),
          ("VOUT > 4.5 V", cross(s, "vout", 4.5, t0=142.55 * ms)),
          ("gates ON -1.1 V (TX)", 143.6 * ms)]
    d = dict(ev)
    chk = [("No re-arm while gates ON (142.7 ms toggle ignored)",
            d["PA_ARMED high (should be after 143.0 ms)"] is not None and d["PA_ARMED high (should be after 143.0 ms)"] > 143.0 * ms,
            fmt(d["PA_ARMED high (should be after 143.0 ms)"]))]
    return ev, chk, [(141.0 * ms, t0), (143.6 * ms, 1)], [("WDT_OK low", t0)], [143.0 * ms], []


def s5b(s):
    t0 = 141.0 * ms
    t05 = cross(s, "vout", 0.5, False, t0)
    ev = [("WDT_OK low (armed, gates -1.75 V, no PA current)", t0),
          ("PA_DRAIN_EN low", cross(s, "pa_drain_en", 0.9, False, t0)),
          ("VOUT < 4.5 V", cross(s, "vout", 4.5, False, t0)),
          ("VOUT < 0.5 V", t05)]
    notes = [f"QOD-only discharge (RPD 400 ohm x 19.81 uF, tau {400 * 19.81e-6 * 1e3:.1f} ms): VOUT < 0.5 V after "
             f"{(t05 - t0) / ms:.2f} ms" if t05 else "VOUT never < 0.5 V",
             "gates stay at -1.75 V, so no PA current flows; the residual charge is 0.25 mJ"]
    return ev, [], [], [("WDT_OK low", t0)], [], notes


def s6(s):
    t0 = 142.0 * ms
    tl = {k: cross(s, *a) for k, a in {
        "aux": ("aux", 2.97, False, t0), "n5v": ("n5v", -4.6, True, t0), "n3v3": ("n3v3", -3.0, True, t0),
        "gate": ("gmax", -0.15, True, t0)}.items()}
    tf = min(v for v in tl.values() if v is not None)
    ev = [("VIN_12V starts falling (12 -> 0 V / 1 ms)", t0),
          ("VIN < 7 V (TPS62933 UVLO stop, AUX stops)", cross(s, "vin", 7, False, t0)),
          ("VIN < 5.3 V (+5V_PA out of regulation)", cross(s, "vin", 5.3, False, t0)),
          ("+3V3_AUX < 2.97 V (AUX UV comparator)", tl["aux"]),
          ("NEG_RAILS_OK low (< VIL)", cross(s, "neg_rails_ok", VIL, False, t0)),
          ("PA_DRAIN_EN low", cross(s, "pa_drain_en", 0.9, False, t0)),
          ("VOUT < 0.5 V", cross(s, "vout", 0.5, False, t0)),
          ("+3V3_AUX < 2.35 V (TPS65131 UVLO)", cross(s, "aux", 2.35, False, t0)),
          ("+3V3_AUX < 2.0 V (LM339 VS min)", cross(s, "aux", 2.0, False, t0)),
          ("+3V3_RF < 2.8 V (ADAR1000 PA_BIAS high-Z, assumed)", cross(s, "v3rf", 2.8, False, t0)),
          ("+1V8_DIG < 1.65 V", cross(s, "v18", 1.65, False, t0)),
          ("-5V_BF > -4.6 V", tl["n5v"]),
          ("-3V3_SW > -3.0 V", tl["n3v3"]),
          ("any gate > -1.0 V (drifting above TX bias)", cross(s, "gmax", -1.0, t0=t0)),
          ("any gate > -0.15 V", tl["gate"]),
          ("NEG_RAILS_OK back > 0.675 V (LM339 below VS min)", cross(s, "neg_rails_ok", 0.675, t0=tf + 5e-6)),
          ("IL_REF back > 0.5 V", cross(s, "il_ref", 0.5, t0=(cross(s, "il_ref", 0.1, False, tf) or tf) + 1e-6)),
          ("IL_EN back high", cross(s, "il_en", 0.9, t0=tf + 5e-6)),
          ("PG_3V3RF low", cross(s, "pg_3v3rf", 0.9, False, t0)),
          ("PG_3V3RF floats high again (TPS568230 VIN < 1.5 V, assumed)", cross(s, "pg_3v3rf", 0.5, t0=(cross(s, "pg_3v3rf", 0.5, False, t0) or t0) + 1e-6)),
          ("NEG_OK back high", cross(s, "neg_ok", 0.9, t0=tf + 5e-6)),
          ("any gate > -0.01 V", cross(s, "gmax", -0.01, t0=t0))]
    after = s["t"] > tf + 5e-6
    toff = cross(s, "il_ref", 0.1, False, tf) or tf
    chk = [("INFO: IL_EN and NEG_OK logic levels stay low after the trip (LVC outputs; hazard checked by EN/REF/PA_DRAIN_EN)",
            max(s["il_en"][after].max(), s["neg_ok"][after].max()) < VIL,
            f"max IL_EN {s['il_en'][after].max():.3f} V, max NEG_OK {s['neg_ok'][after].max():.3f} V", "info"),
           ("PA_DRAIN_EN stays < VENF 1.08 V after trip",
            s["pa_drain_en"][after].max() < 1.08, f"max {s['pa_drain_en'][after].max():.3f} V", "safety"),
           ("INFO: NEG_RAILS_OK level after trip (pull-up AUX/2 once LM339 < VS min)",
            s["neg_rails_ok"][after].max() < VIL, f"max {s['neg_rails_ok'][after].max():.3f} V", "info"),
           ("INFO: IL_REF stays off (< 0.1 V) once switched off", s["il_ref"][s["t"] > toff + 1e-6].max() < 0.1,
            f"max {s['il_ref'][s['t'] > toff + 1e-6].max():.3f} V", "info")]
    m = s["t"] > t0
    notes = [f"first interlock threshold crossed: {min(tl, key=lambda k: tl[k] or 1)} at {fmt(tf)}",
             f"drain < 0.5 V {dt_us(tl['gate'], cross(s, 'vout', 0.5, False, t0))} before the first gate reaches -0.15 V",
             f"max gate after VIN loss {s['gmax'][m].max() * 1e3:+.0f} mV; max NEG_OK after trip "
             f"{s['neg_ok'][s['t'] > tf + 1e-5].max():.2f} V; max IL_EN after trip {s['il_en'][s['t'] > tf + 1e-5].max():.2f} V; max PA_ARMED after trip {s['pa_armed'][s['t'] > tf + 1e-5].max():.2f} V"]
    return ev, chk, [(141.0 * ms, tf)], [("first monitored threshold (VIN loss)", tf)], [], notes


def s7(s, label, by_en):
    t0 = 142.0 * ms
    tuv = cross(s, "v3rf", 0.85 * 3.327, False, t0)
    tf = t0 if by_en else tuv
    tg = cross(s, "gmax", -0.15, t0=t0)
    ev = [(label, t0),
          ("+3V3_RF < 85 % (PGOOD UV)", tuv),
          ("PG_3V3RF low", cross(s, "pg_3v3rf", 0.9, False, t0)),
          ("IL_EN low", cross(s, "il_en", 0.9, False, t0)),
          ("NEG_OK low", cross(s, "neg_ok", 0.9, False, t0)),
          ("PA_DRAIN_EN low", cross(s, "pa_drain_en", 0.9, False, t0)),
          ("TPS22810 switch open (tOFF done)", cross(s, "sw_en_d", 0.5, False, t0)),
          ("IL_REF < 0.1 V", cross(s, "il_ref", 0.1, False, t0)),
          ("+3V3_RF < 2.8 V (ADAR1000 PA_BIAS high-Z, assumed)", cross(s, "v3rf", 2.8, False, t0)),
          ("VOUT < 0.5 V", cross(s, "vout", 0.5, False, t0)),
          ("any gate > -1.0 V", cross(s, "gmax", -1.0, t0=t0)),
          ("any gate > -0.15 V", tg)]
    m = s["t"] > t0
    notes = [f"-5V_BF {s['n5v'][-1]:.2f} V and -3V3_SW {s['n3v3'][-1]:.2f} V at sim end (still up: AVDD1/VSS_SW "
             "present without AVDD3/VDD_SW; ADAR1000/ADTR1107 power-down order is not specified in the datasheets)",
             f"max gate after the fault {s['gmax'][m].max() * 1e3:+.0f} mV; drain < 0.5 V "
             f"{dt_us(tg, cross(s, 'vout', 0.5, False, t0))} before any gate reaches -0.15 V"]
    return ev, [], [(141.0 * ms, tf)], [(label if by_en else "+3V3_RF < 85 %", tf)], [], notes




SCEN = [("s1_powerup", "S1 normal power-up", s1, [(0, 141.5), (139.95, 141.5)]),
        ("s2_unprogrammed_gates", "S2 MCU_PA_EN with unprogrammed / unpinched gates", s2, [(139.9, 141.5)]),
        ("s3_gate_lost", "S3 gate lost during TX", s3, [(141.98, 142.12)]),
        ("s4a_neg_collapse_enn", "S4a -5V_BF collapse via TPS65131 ENN", lambda s: s4(s, "PWR_EN_NEG / ENN low"), [(141.9, 147)]),
        ("s4b_neg_collapse_ldo", "S4b -5V_BF collapse via TPS7A33 disable", lambda s: s4(s, "-5V_BF LDO disabled"), [(141.9, 145)]),
        ("s5a_watchdog_tx", "S5a watchdog fault during TX + recovery", s5a, [(141.9, 144)]),
        ("s5b_watchdog_idle", "S5b watchdog fault while armed, gates pinched", s5b, [(140.95, 141.3)]),
        ("s6_vin_loss", "S6 VIN_12V loss during TX", s6, [(141.95, 143.2)]),
        ("s7a_rf_en_loss", "S7a +3V3_RF lost via PWR_EN_3V3 (neg rails up)", lambda s: s7(s, "PWR_EN_3V3 low", True), [(141.98, 142.3)]),
        ("s7b_rf_silent_collapse", "S7b +3V3_RF silent collapse, EN high (neg rails up)", lambda s: s7(s, "+3V3_RF converter stops", False), [(141.98, 142.3)])]
# (design, mode) combinations run on the scenario suite; CAP only on the fault scenarios where it matters
S_RUNS = [(d, m) for d in ("ASB", "R2") for m in ("nom", "pess")]
CORNERS = [k for k in DESIGNS if k.startswith("ASB_")]
FIXES = ["FIX", "FIX_slow", "FIX_ovl"]
CAP_SCEN = ("s3_gate_lost", "s5a_watchdog_tx", "s5b_watchdog_idle", "s6_vin_loss")
FAULT_SCEN = ("s3_gate_lost", "s4a_neg_collapse_enn", "s4b_neg_collapse_ldo", "s5a_watchdog_tx", "s5b_watchdog_idle",
              "s6_vin_loss", "s7a_rf_en_loss", "s7b_rf_silent_collapse")


def s_job(args):
    name, design, mode = args
    with tempfile.TemporaryDirectory() as tmp:
        params = {**DESIGNS[design][0], **MODES[mode]}
        s = run_variant(open(os.path.join(HERE, name + ".cir")).read(), params, tmp, name)
    fn = {n: f for n, _, f, _ in SCEN}[name]
    ev, chk, tx, faults, rearm, notes = fn(s)
    sres, met, cb = check_safety(s, tx, faults, rearm)
    res = [c if len(c) == 4 else (*c, "safety") for c in chk] + sres
    if (design, mode) in (("ASB", "pess"), ("R2", "nom")):
        title = {n: t for n, t, _, _ in SCEN}[name]
        plot(f"{name}_{design}_{mode}", f"{title} [{design}, {mode} logic]", s,
             {n: w for n, _, _, w in SCEN}[name][-1:])
    return dict(name=name, design=design, mode=mode, ev=ev, res=res, met=met, cb=cb, notes=notes)


# ------------------------------------------------------------------ D: arbitrary rail ordering (free-rail mode)
RAILS = ["aux", "18", "rf", "pa", "n5", "n3"]
RAIL_NAMES = {"aux": "+3V3_AUX", "18": "+1V8_DIG", "rf": "+3V3_RF", "pa": "+5V_PA", "n5": "-5V_BF", "n3": "-3V3_SW"}
TR_RANGE = {"aux": (0.2, 2), "18": (0.1, 1), "rf": (0.3, 3), "pa": (0.3, 3), "n5": (0.5, 5), "n3": (0.5, 5)}


def step_pwl(v0, events):
    pts, cur, last = [(0.0, v0)], v0, 0.0
    for T, v in sorted(events):
        T = max(T, last + 2e-6)
        pts += [(T, cur), (T + 1e-6, v)]
        cur, last = v, T + 1e-6
    return "PWL(" + " ".join(f"{a:.9g} {b:.6g}" for a, b in pts) + ")"


def d_netlist(sch):
    r = sch
    L = [f"* D ordering run {r['id']} -- BEHAVIOURAL / PRELIMINARY (free-rail mode, ADAR1000 register reset)",
         f"* rails on/off (ms): " + "; ".join(f"{RAIL_NAMES[k]} {r['rail'][k]}" for k in RAILS),
         ".include h2c_plant.inc",
         ".param free=1 adar_reset=1 " + " ".join(f"tr_{k}={r['tr'][k]:.3f}" for k in RAILS),
         f"VVIN vin 0 {step_pwl(12, r['vin_off'])}",
         "VE3 fw_en3v3 0 1", "VE5 fw_en5vpa 0 1", "VEN fw_enneg 0 1", "VKL ldo5_kill 0 0", "VRK rf_kill 0 0",
         f"VWD fw_wdt 0 {step_pwl(1, r['wdt'])}",
         f"VPA fw_pa_en 0 {step_pwl(0, r['paen'])}"]
    for g in range(4):
        L.append(f"VD{g + 1} dac{g + 1} 0 {step_pwl(0, [(t, v[g]) for t, v in r['writes']])}")
    L.append(f"VTLW tlw 0 {step_pwl(0, [(t, t) for t, _ in r['writes']])}")
    for i, k in enumerate(RAILS):
        ev = []
        for a, b in r["rail"][k]:
            ev.append((a * ms, 1))
            if b is not None:
                ev.append((b * ms, 0))
        L.append(f"VFR{i + 1} fr_{k} 0 {step_pwl(0, ev)}")
    L += [f".tran 1u {r['tend'] * ms:.6g} 0 2u", ".end", ""]
    return "\n".join(L)


def gen_perm(i, up, down, rng):
    tr = {k: rng.uniform(*TR_RANGE[k]) for k in RAILS}
    t, rail = 0.5, {}
    for k in up:
        rail[k] = [t, None]
        t += 0 if rng.random() < 0.15 else rng.uniform(0, 1.5)
    t_up = max(rail[k][0] + tr[k] for k in RAILS)
    t_ready = max(t_up + 1.5, rail["18"][0] + tr["18"] + 10.5, rail["rf"][0] + tr["rf"] + 2.0)
    w1, arm, tx = t_ready + 0.2, t_ready + 0.4, t_ready + 1.2
    t = tx + 0.4 + rng.uniform(0, 0.3)
    for k in down:
        rail[k][1] = t
        t += 0 if rng.random() < 0.15 else rng.uniform(0, 1.0)
    return dict(id=f"P{i:03d}", kind="perm", tr=tr, rail={k: [tuple(rail[k])] for k in RAILS}, vin_off=[], wdt=[],
                paen=[(arm * ms, 1)], writes=[(w1 * ms, (-1.75,) * 4), (tx * ms, (-1.1,) * 4)], tend=t + 4,
                order=("up: " + ">".join(RAIL_NAMES[k] for k in up) + " | down: " + ">".join(RAIL_NAMES[k] for k in down)))


def gen_random(i, rng):
    tr = {k: rng.uniform(*TR_RANGE[k]) for k in RAILS}
    rail = {}
    for k in RAILS:
        on = rng.uniform(0.2, 8)
        segs = [(on, None)]
        if rng.random() < 0.4:
            off = rng.uniform(on + 2, 30)
            segs = [(on, off)]
            if rng.random() < 0.5:
                segs.append((rng.uniform(off + 0.3, 33), None))
        rail[k] = segs
    vin_off = []
    if rng.random() < 0.15:   # VIN loss takes +3V3_RF, +5V_PA and +3V3_AUX with it (they are derived from VIN)
        tv = rng.uniform(10, 30)
        vin_off = [(tv * ms, 0)]
        for k in ("rf", "pa", "aux"):
            rail[k] = [(a, b if (b is not None and b < tv) else (tv if a < tv else b)) for a, b in rail[k] if a < tv]
            if not rail[k]:
                rail[k] = [(0.2, tv)]
    writes, paen, wdt = [], [], []
    for _ in range(rng.integers(1, 5)):
        writes.append((rng.uniform(0.5, 35) * ms, tuple([rng.choice([-1.75, -1.75, -1.1, 0.0])] * 4)))
    if rng.random() < 0.3:
        writes.append((rng.uniform(0.5, 35) * ms, (0.0, -1.1, -1.1, -1.1)))
    t = rng.uniform(0.5, 30)
    for _ in range(rng.integers(1, 4)):
        paen += [(t * ms, 1), ((t + rng.uniform(0.05, 6)) * ms, 0)]
        t += rng.uniform(6.1, 12)
    if rng.random() < 0.6:       # one proper arming sequence at a random time (also possibly too early)
        ts = rng.uniform(5, 30)
        writes += [(ts * ms, (-1.75,) * 4), ((ts + 1.0) * ms, (-1.1,) * 4)]
        paen += [((ts + 0.2) * ms, 1), ((ts + rng.uniform(2, 6)) * ms, 0)]
    if rng.random() < 0.3:
        tw = rng.uniform(5, 35)
        wdt = [(tw * ms, 0), ((tw + rng.uniform(0.1, 2)) * ms, 1)]
    paen = sorted(paen)
    return dict(id=f"R{i:03d}", kind="random", tr=tr, rail={k: [tuple(x) for x in rail[k]] for k in RAILS},
                vin_off=vin_off, wdt=wdt, paen=paen, writes=sorted(writes), tend=40, order="random")


def d_eval(s, r):
    t = s["t"]
    valid = supplies_valid(s)
    def steps(v0, ev):
        pts = [(0.0, v0)]
        for a, b in sorted(ev):
            pts += [(a, pts[-1][1]), (a + 1e-6, b)]
        return np.interp(t, *zip(*pts)) > 0.5
    wdt_ok = steps(1.0, r["wdt"])
    paen = steps(0.0, r["paen"])
    adar_up = s["v3rf"] > 2.8
    # legitimate armed-TX windows: arm edge after an all-pinched write (>= 50 us earlier), everything valid since
    # that write, MCU_PA_EN held, then a TX (-1.1) write; window ends at the first fault / stop / new write
    writes = sorted(r["writes"])
    tx = []
    arm_edges = [a for a, b in r["paen"] if b == 1]
    for j, (tw, v) in enumerate(writes):
        if not all(x == -1.1 for x in v):
            continue
        prev = [w for w in writes[:j]]
        arms = [a for a in arm_edges if a < tw]
        if not prev or not arms:
            continue
        ta = arms[-1]
        pw = [w for w in prev if w[0] < ta]
        if not pw or not all(x == -1.75 for x in pw[-1][1]) or ta - pw[-1][0] < 50e-6 or \
                any(ta < w[0] < tw and not all(x == -1.75 for x in w[1]) for w in prev):
            continue
        seg = (t >= ta - 50e-6) & (t <= tw)
        if not (valid[seg].all() and adar_up[(t >= pw[-1][0]) & (t <= tw)].all() and wdt_ok[seg].all()
                and paen[(t >= ta + 2e-6) & (t <= tw)].all()):
            continue
        nxt = [w[0] for w in writes[j + 1:]]
        stop = (~valid | ~wdt_ok | ~paen | (s["gmax"] > -0.15)) & (t > tw)
        te = min([t[stop][0]] if stop.any() else [t[-1]] + nxt)
        tx.append((tw, te))
    fault = ~valid | ~wdt_ok | ~paen | (s["gmax"] > -0.15)
    fo = [tf for tf in onsets(fault, t) if at(s, "vout", tf) > VDRAIN or at(s, "sw_en_d", tf) > 0.5]
    res, met, cb = check_safety(s, tx, [(f"fault@{tf / ms:.3f}ms", tf) for tf in fo], arm_edges)
    out = dict(id=r["id"], kind=r["kind"], order=r["order"], gmax=float(s["gmax"].max()), gmin=float(s["gmin"].min()),
               t05=max([m["t05"] for m in met if m["t05"] is not None], default=None),
               react=max([m["react"] for m in met if m["react"] is not None], default=None),
               nfault=len(fo), ntx=len(tx), cb=cb,
               fails=[(c, d) for c, ok, d, k in res if k == "safety" and not ok])
    return out


def d_job(args):
    r, design, mode = args
    with tempfile.TemporaryDirectory() as tmp:
        s = run_variant(d_netlist(r), {**DESIGNS[design][0], **MODES[mode]}, tmp, r["id"])
    out = d_eval(s, r)
    out.update(design=design, mode=mode)
    return out


def d_schedules(quick):
    rng = np.random.default_rng(20261112)
    perms = list(itertools.permutations(RAILS))
    downs = perms.copy()
    rng.shuffle(downs)
    runs = [gen_perm(i, up, down, rng) for i, (up, down) in enumerate(zip(perms, downs))]
    runs += [gen_random(i, rng) for i in range(200)]
    return runs[::15] + runs[720::10] if quick else runs


# ------------------------------------------------------------------ plotting
def plot(name, title, s, wins):
    t = s["t"] / ms
    for j, (a, b) in enumerate(wins):
        m = (t >= a) & (t <= b)
        fig, ax = plt.subplots(4, 1, figsize=(11, 11), sharex=True)
        for k, lab in [("vin", "VIN_12V"), ("aux", "+3V3_AUX"), ("v18", "+1V8_DIG"), ("v3rf", "+3V3_RF (AVDD3)"),
                       ("v5pa", "+5V_PA"), ("vneg", "PWR_VNEG"), ("n5v", "-5V_BF (AVDD1)"), ("n3v3", "-3V3_SW (VSS_SW)")]:
            ax[0].plot(t[m], s[k][m], label=lab)
        ax[0].set_ylabel("rail [V]")
        for i, (k, lab) in enumerate([("pg_3v3rf", "PG_3V3RF"), ("enn", "ENN"), ("neg_rails_ok", "NEG_RAILS_OK"),
                                      ("il_en", "IL_EN"), ("gates_ok", "GATES_OK"), ("gates_pinched", "GATES_PINCHED"),
                                      ("neg_ok", "NEG_OK"), ("wdt_ok", "WDT_OK"), ("mcu_pa_en", "MCU_PA_EN"),
                                      ("pa_armed", "PA_ARMED"), ("pa_drain_en", "PA_DRAIN_EN"),
                                      ("sw_en_d", "TPS22810 on (tOFF delayed)")]):
            ax[1].plot(t[m], s[k][m] + 2.2 * i, lw=1.2)
            ax[1].text(a, 2.2 * i + 0.3, " " + lab, fontsize=7, va="bottom")
        ax[1].set_yticks([]); ax[1].set_ylabel("logic (offset)")
        for k in range(1, 5):
            ax[2].plot(t[m], s[f"gate{k}"][m], label=f"VGG_PA{k}")
        ax[2].plot(t[m], s["il_ref"][m], "k:", label="IL_REF")
        for y, c in [(0, "k"), (-0.15, "r"), (-1.5, "orange"), (-2.0, "k")]:
            ax[2].axhline(y, color=c, ls="--", lw=0.8)
        ax[2].set_ylabel("gate [V]")
        ax[3].plot(t[m], s["vout"][m], "k", label="VOUT (+5V_PA_C1 / VDD_PA)")
        ax[3].axhline(0.5, color="r", ls="--", lw=0.8)
        a3 = ax[3].twinx()
        for k in range(1, 5):
            a3.plot(t[m], s[f"ipa{k}"][m], lw=0.9, label=f"I_PA{k}")
        if s["icb"].max() > 1e-3:
            a3.plot(t[m], s["icb"][m] / 10, "m--", lw=1, label="I_crowbar / 10")
        a3.set_ylabel("current [A]")
        ax[3].set_ylabel("drain [V]"); ax[3].set_xlabel("time [ms]")
        for x in (ax[0], ax[2], ax[3]):
            x.legend(fontsize=7, loc="upper left", ncol=4); x.grid(alpha=0.3)
        a3.legend(fontsize=7, loc="upper right")
        fig.suptitle(f"{title} -- BEHAVIOURAL / PRELIMINARY, datasheet timing, not hardware-validated", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, f"h2c_{name}{'' if j == 0 else '_zoom'}.png"), dpi=100)
        plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    quick = "--quick" in sys.argv
    workers = max(1, min(48, (os.cpu_count() or 2) - 2))
    jobs = [(n, d, m) for n, *_ in SCEN for d, m in S_RUNS] + \
        [(n, c, "pess") for n, *_ in SCEN for c in CORNERS + FIXES] + [(n, "FIX", "nom") for n, *_ in SCEN]
    d_designs = [("ASB", "nom"), ("ASB", "pess"), ("ASB_td20", "pess"), ("ASB_td50", "pess"), ("ASB_td100", "pess"),
                 ("ASB_slow", "pess"), ("ASB_ovl", "pess"), ("R2", "nom"), ("FIX", "nom"), ("FIX", "pess"),
                 ("FIX_slow", "pess"), ("FIX_ovl", "pess")]
    with ProcessPoolExecutor(workers) as ex:
        sres = list(ex.map(s_job, jobs))
        sch = d_schedules(quick)
        dres = list(ex.map(d_job, [(r, d, m) for d, m in d_designs for r in sch], chunksize=4))
    gating_ok, fails = True, []
    for r in sres:
        bad = [(c, x) for c, ok, x, k in r["res"] if k == "safety" and not ok]
        if bad and DESIGNS[r["design"]][2]:
            gating_ok = False
            fails += [f"{r['design']}/{r['mode']} {r['name']}: {c} -- {x}" for c, x in bad]
    for r in dres:
        if r["fails"] and DESIGNS[r["design"]][2]:
            gating_ok = False
            fails += [f"{r['design']}/{r['mode']} ordering {r['id']}: {c} -- {x}" for c, x in r["fails"]]
    L = ["# H2-C sequencing / interlock simulation results -- revision 3 (as built)", "",
         f"**Gating result (as-built design ASB incl. all corners, nominal + pessimistic): {'PASS' if gating_ok else 'FAIL'}**", "",
         "**BEHAVIOURAL / PRELIMINARY -- not hardware-validated.** ngspice behavioural models with datasheet timing. "
         "Generated by `run_h2c_sim.py`. Every ASB* design gates the exit code; R2 is shown for comparison.", "",
         "Designs: " + "; ".join(f"**{k}** = {v[1]}" for k, v in DESIGNS.items()), "",
         "Logic modes: **nom** = nominal thresholds; **pess** = every comparator / LVC / enable input inside its "
         "undefined band taken as HIGH / ON (LVC with VCC < 1.65 V outputs VCC, flop SET).", ""]
    by = {(r["name"], r["design"], r["mode"]): r for r in sres}
    short = lambda c: c.split(":")[0].split(" ")[0]
    cols = S_RUNS + [(c, "pess") for c in CORNERS] + [("FIX", "nom")] + [(c, "pess") for c in FIXES]
    L += ["## Scenario suite: safety result per design / logic mode", "",
          "| scenario | " + " | ".join(f"{d}/{m}" for d, m in cols) + " |", "|---|" + "---|" * len(cols)]
    for n, title, *_ in SCEN:
        cells = []
        for d, m in cols:
            r = by[(n, d, m)]
            bad = sorted({short(c) for c, ok, _, k in r["res"] if k == "safety" and not ok})
            cells.append("PASS" if not bad else "**FAIL** " + ",".join(bad))
        L.append(f"| {title} | " + " | ".join(cells) + " |")
    f_us = lambda x: "never" if x is None else f"{x * 1e6:.1f} us"
    L += ["", "## Fault response (times from the fault threshold crossing)", "",
          "| scenario | design/mode | switch open | drain < 0.5 V | residual PA energy | peak PA I | crowbar peak / energy | "
          "crowbar starts after switch open | crowbar off before VOUT ramp |", "|---|---|---|---|---|---|---|---|---|"]
    for n, title, *_ in SCEN:
        for d, m in (("R2", "nom"), ("ASB", "nom"), ("ASB", "pess")):
            r = by[(n, d, m)]
            if not r["met"]:
                continue
            q, cb = r["met"][0], r["cb"] or {}
            L.append(f"| {title} | {d}/{m} | {f_us(q['react'])} | {f_us(q['t05'])} | {q['e'] * 1e3:.3f} mJ | {q['ipk']:.3f} A | "
                     + (f"{cb['i_pk']:.1f} A / {cb['e_cb'] * 1e3:.3f} mJ | {fmtu(cb['bbm_off_us'])} | {fmtu(cb['bbm_on_us'])} |"
                        if cb.get("i_pk") else "- | - | - |"))
    L += ["", "## Corners (pessimistic logic, worst over all scenarios with a fault)", "",
          "| corner | safety | worst drain < 0.5 V | worst switch open | max PA energy | max peak PA I | max crowbar peak | "
          "min crowbar start after switch open | min crowbar-off before VOUT ramp | max crowbar/switch overlap |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for c in ["ASB"] + CORNERS + FIXES:
        rs = [by[(n, c, "pess")] for n, *_ in SCEN]
        ms_ = [q for r in rs for q in r["met"]]
        cbs = [r["cb"] for r in rs if r["cb"] and r["cb"].get("i_pk")]
        nb = sum(1 for r in rs for _, ok, _, k in r["res"] if k == "safety" and not ok)
        mx = lambda k: max([q[k] for q in ms_ if q[k] is not None], default=None)
        L.append(f"| {c} | {'PASS' if not nb else f'**FAIL** ({nb})'} | {f_us(mx('t05'))} | {f_us(mx('react'))} | "
                 f"{mx('e') * 1e3:.3f} mJ | {mx('ipk'):.3f} A | {max(x['i_pk'] for x in cbs):.1f} A | "
                 f"{fmtu(min([x['bbm_off_us'] for x in cbs if x['bbm_off_us'] is not None], default=None))} | "
                 f"{fmtu(min([x['bbm_on_us'] for x in cbs if x['bbm_on_us'] is not None], default=None))} | "
                 f"{max(x['overlap_us'] for x in cbs):.2f} us |")
    # M5 summary
    L += ["", "## M5: PG_3V3RF sink level and BAT54C clamps (worst over every as-built run, scenarios + ordering)", "",
          "| design/mode | max PG_3V3RF while asserted (TLV755 EN off <= 0.3 V) | max clamped PA_DRAIN_EN (< 1.08 V) | "
          "max IL_CLR_N - VIL (< 0) | max TPS386000 sink (<= 5 mA) |", "|---|---|---|---|---|"]
    allr = [(r["design"], r["mode"], (r["cb"] or {}).get("m5")) for r in sres] + \
           [(r["design"], r["mode"], (r["cb"] or {}).get("m5")) for r in dres]
    for d, m in sorted({(d, m) for d, m, _ in allr if d != "R2"}):
        m5 = [x for dd, mm, x in allr if dd == d and mm == m and x]
        if m5:
            L.append(f"| {d}/{m} | {max(x['pg'] for x in m5):.3f} V | {max(x['pd'] for x in m5):.3f} V | "
                     f"{max(x['clr'] for x in m5) * 1e3:+.0f} mV | {max(x['isup'] for x in m5) * 1e3:.2f} mA |")
    # ordering test
    L += ["", f"## Ordering test ({len(sch)} runs per design: {sum(r['kind'] == 'perm' for r in sch)} start/stop "
          f"permutations + {sum(r['kind'] == 'random' for r in sch)} random)", "",
          "| design/mode | failing runs | failures by criterion | worst VGG max | worst VGG min | worst drain < 0.5 V after fault | "
          "worst switch open | crowbar overlap max / min start after switch open |", "|---|---|---|---|---|---|---|---|"]
    worst = {}
    for d, m in d_designs:
        rs = [r for r in dres if r["design"] == d and r["mode"] == m]
        fl = [r for r in rs if r["fails"]]
        crit = {}
        for r in fl:
            for c, _ in r["fails"]:
                crit[short(c)] = crit.get(short(c), 0) + 1
        gx = max(rs, key=lambda r: r["gmax"]); gn = min(rs, key=lambda r: r["gmin"])
        t5 = max(rs, key=lambda r: r["t05"] or 0); rc = max(rs, key=lambda r: r["react"] or 0)
        cbs = [r["cb"] for r in rs if r["cb"] and r["cb"].get("i_pk")]
        ovl = max([c["overlap_us"] for c in cbs], default=None)
        bbm = min([c["bbm_off_us"] for c in cbs if c.get("bbm_off_us") is not None], default=None)
        L.append(f"| {d}/{m} | {len(fl)} / {len(rs)} | {', '.join(f'{k}:{v}' for k, v in sorted(crit.items())) or '-'} | "
                 f"{gx['gmax'] * 1e3:+.0f} mV ({gx['id']}) | {gn['gmin']:.3f} V ({gn['id']}) | "
                 f"{(t5['t05'] or 0) * 1e6:.1f} us ({t5['id']}) | {(rc['react'] or 0) * 1e6:.1f} us ({rc['id']}) | "
                 + (f"{ovl:.2f} us / {fmtu(bbm)} |" if cbs else "- |"))
        worst[(d, m)] = dict(gmax=gx, gmin=gn, t05=t5, fail=fl[0] if fl else None)
    L += ["", "## Every as-built FAIL", ""] + ([f"- {x}" for x in fails[:200]] or ["- none"])
    if len(fails) > 200:
        L.append(f"- ... {len(fails) - 200} more (see h2c_d_runs.json)")
    L += ["", "### Worst-case waveforms", ""]
    sch_by = {r["id"]: r for r in sch}
    with tempfile.TemporaryDirectory() as tmp:
        for (d, m), w in worst.items():
            if d not in ("ASB", "ASB_slow", "ASB_ovl", "ASB_td100", "R2", "FIX"):
                continue
            for kind in ("gmax", "gmin", "t05", "fail"):
                if w[kind] is None:
                    continue
                rid = w[kind]["id"]
                fn = f"d_worst_{d}_{m}_{kind}.cir"
                open(os.path.join(HERE, fn), "w").write(with_params(d_netlist(sch_by[rid]), {**DESIGNS[d][0], **MODES[m]}))
                s = ngrun(os.path.join(HERE, fn), os.path.join(tmp, "w.dat"))
                plot(f"d_worst_{d}_{m}_{kind}", f"Ordering worst {kind}: {rid} [{d}, {m}] {sch_by[rid]['order']}", s,
                     [(0, s["t"][-1] / ms)])
                L.append(f"- `{fn}` / `h2c_d_worst_{d}_{m}_{kind}.png`: {rid} ({sch_by[rid]['order']})")
    for d, m in (("ASB", "pess"), ("ASB", "nom"), ("R2", "nom")):
        L += ["", f"## Details: {d} / {m}", ""]
        for n, title, *_ in SCEN:
            r = by[(n, d, m)]
            L += [f"### {title} (`{n}.cir`)", "", "| event | time |", "|---|---|"]
            L += [f"| {e} | {fmt(tv)} |" for e, tv in sorted(r["ev"], key=lambda e: 9 if e[1] is None else e[1])]
            L += ["", "| check | kind | result | detail |", "|---|---|---|---|"]
            L += [f"| {c} | {k.upper()} | {'PASS' if ok else '**FAIL**'} | {x} |" for c, ok, x, k in r["res"]]
            L += [""] + [f"- {x}" for x in r["notes"]] + [""]
    json.dump(dres, open(os.path.join(HERE, "h2c_d_runs.json"), "w"), default=str, indent=0)
    open(os.path.join(HERE, "h2c_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:60]))
    return 0 if gating_ok else 1


if __name__ == "__main__":
    sys.exit(main())
