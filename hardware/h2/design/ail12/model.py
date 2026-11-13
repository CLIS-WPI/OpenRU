"""A-IL12 BEHAVIOURAL transient model (PRELIMINARY; not hardware-validated; not a TI or onsemi model).

Event-driven ODE model written for this study because the official TI TPS25947 transient model (SLVMDJ6) is
Cadence-encrypted and runs only in PSpice. It covers the U1 regulator-short fault from the bench VIN source to +5V_IL, the
permit node P, SHDN_c and the TPS16630 (U10) FET-off decision. The crowbar and drain discharge are NOT simulated: the H2-D
budget tail (P sink asserted -> drain < 0.5 V <= 16.5 us) is added afterwards.

Modelling limits (also in the report):
  * TPS25947: ideal comparators with the datasheet thresholds; the response delays tOVLO, tSC, the AUXOFF de-assertion delay,
    the 30 us fast-trip de-glitch and tSWOV are model PARAMETERS (datasheet typicals by default, swept as HYPOTHETICAL).
    The FET is a resistor (Ron) with ideal reverse blocking; slew-controlled start-up is an idealised ramp; active current
    limit is instantaneous (tLIM ignored). The off-state forward leakage (VIN > VOUT) is unspecified: parameter i_leak.
  * TPS7A2550: transconductance source with current limit and a dropout resistance. A pass-element short is a conductance
    ramp between its IN and OUT.
  * TPS3703: comparator + fixed delays (tPD 30 us max applied at 5 % overdrive, tD, tPD(MR)); RESET is a 50 ohm sink
    (VOL 0.25 V at 5 mA).  TLV3201 (CD): ideal comparator + 55 ns.  MOSFETs: level-1 square law fitted to datasheet max
    rDS(on) at the chosen VGS(th) corner (25 C data only).
  * Loads on +5V_IL are lumped (i_il, ASSUMED); bench source = ideal source -> optional current limit -> output capacitor
    -> cable R + L.
"""
import heapq
import itertools
import math
from dataclasses import dataclass, field, replace

import numpy as np
from params import v
from scipy.integrate import solve_ivp

NS = ['v_src', 'i_l', 'v_vin', 'v_ldo', 'v_in', 'v_out', 'v_vcb', 'v_p', 'v_shdn', 'v_ramp', 'v_x']
IX = {n: i for i, n in enumerate(NS)}


@dataclass
class Cfg:
    name: str = 'base'
    iface: str = 'corrected'          # 'corrected' (2N7002 inverter -> P and U3 MR), 'bss84' (proposal), 'none'
    # bench source
    vset: tuple = ((0.0, 13.2),)      # piecewise-linear (t, V) of the ideal source
    r_int: float = 5e-3
    i_cc: float = math.inf            # current limit of the ideal source
    t_cc: float = 0.0                 # CC loop not active until t_fault + t_cc (finite response)
    c_src: float = 470e-6
    i_sink: float = 1.0               # bench down-programmer sink capability (ASSUMED)
    r_cab: float = 20e-3
    l_cab: float = 0.5e-6
    c1: float = 1e-6 * 0.9 * 0.85 * 0.6   # C1 1 uF 25 V X7R at 12 V (ASSUMED derating)
    # U1 and the fault
    vldo: float = v('vldo', 1)
    icl: float = v('icl_ldo', 1)
    gm_ldo: float = 20.0
    r_do: float = v('vdo_ldo') / 0.3
    c2: float = 4.7e-6 * 0.9 * 0.85 * 0.675   # CL21A475KAQNNNE (25 V 0805) at 5 V, ASSUMED mid derating
    t_fault: float = math.inf
    r_short: float = 0.1
    t_edge: float = 10e-9
    t_clear: float = math.inf         # short removed at t_fault + t_clear
    # eFuse input RC and dividers (dividers sit on U1 OUT = v_ldo)
    r_in: float = 2.2
    c_in: float = 1e-6 * 0.9 * 0.85 * 0.475   # CL10B105KA8NNNC at 5..13 V, ASSUMED mid derating
    r_ov: tuple = (10.0e3, 2.94e3)
    r_en: tuple = (100e3, 37.4e3)
    # TPS25947 (thresholds index 0/1/2 = min/typ/max)
    th: int = 1
    ron: float = v('ron_typ')
    ilim: float = 3334 / 6490
    isc_gain: float = v('isc_gain')
    ft_enabled: bool = True
    t_ovlo: float = v('t_ovlo')
    t_sc: float = v('t_sc')
    t_aux: float = v('t_ovlo')        # AUXOFF de-assert delay after the OVLO comparator trips (UNSPECIFIED)
    t_deglitch: float = v('t_ft_deglitch')
    t_swov: float = v('t_swov')
    sr: float = v('idvdt', 1) * v('sr_gain', 1) / 2.2e-9
    i_leak: float = 0.0               # off-state IN->OUT leakage (UNSPECIFIED) - HYPOTHETICAL
    # +5V_IL
    c_out: float = (47e-6 * 0.9 * 0.85 * 0.65 + 4.7e-6 * 0.9 * 0.85 * 0.5 + 6 * 0.1e-6 * 0.9 * 0.85 * 0.875)
    i_il: float = v('i_il', 1)
    c5: float = 10e-6 * 0.9 * 0.85 * 0.6
    # P interface
    r_a: tuple = (100e3, 1.0e6)       # AUXOFF pull-up to +5V_IL / to GND
    vaux_ol: float = 0.0              # AUXOFF low level when asserted low (UNSPECIFIED; 0 V typ)
    r_x: float = 10e3
    vth_n: float = 2.5
    rds_n: float = v('n7002_rds', 0)
    vth_p: float = 2.0                # |VGS(th)| of the BSS84
    rds_p: float = v('bss84_rds')
    # supervisors and downstream
    u3_uv: float = v('u3_uv', 1)
    u3_ov: float = v('u3_ov', 1)
    u3_od: float = 0.05
    tpd: float = v('tpd_3703')
    td: float = v('td_3703', 0)
    tpd_mr: float = v('tpd_mr')
    t_end: float = 2e-3
    max_step_fast: float = 20e-9
    fast_window: float = 150e-6
    max_step_slow: float = 20e-6
    init: str = 'steady'              # 'steady' or 'off'


def nmos_i(vgs, vds, vth, rds_spec, vgs_spec=5.0):
    """Level-1 NMOS, k fitted so that rDS(on) = rds_spec at vgs_spec (triode, small vds)."""
    if vgs <= vth or vds <= 0:
        return 0.0
    k = 1.0 / (rds_spec * (vgs_spec - vth))
    vov = vgs - vth
    return k * (vov * vds - 0.5 * vds * vds) if vds < vov else 0.5 * k * vov * vov


@dataclass
class Logic:
    ef: str = 'on'          # off / start / on / cl
    uv_ok: bool = True
    ovlo: bool = False      # comparator state
    ovlo_off: bool = False  # FET forced off by OVLO
    ft_off: bool = False
    aux: bool = True        # AUXOFF released (high)
    short: bool = False
    u3: set = field(default_factory=set)  # active U3 assert causes
    u3_reset: bool = False
    u3_pend: set = field(default_factory=set)
    mr_low: bool = False
    cd: bool = False
    cd_cmd: bool = False
    u10_shdn_ok: bool = True
    u10_uv_ok: bool = True
    u10_on: bool = True
    tok: int = 0


class Sim:
    def __init__(self, c: Cfg):
        self.c = c
        self.L = Logic()
        self.q = []          # scheduled (t, seq, action, token)
        self.seq = 0
        self.log = []        # (t, text)
        self.segs = []       # (t, y, Logic snapshot)
        th = c.th
        self.vov_r, self.vov_f = v('vov_r', th), v('vov_f', th)
        self.vuvlo_r, self.vuvlo_f = v('vuvlo_r', th), v('vuvlo_f', th)
        self.vuvp_r, self.vuvp_f = v('vuvp_r', th), v('vuvp_f', th)
        self.k_ov = c.r_ov[1] / sum(c.r_ov)
        self.k_en = c.r_en[1] / sum(c.r_en)
        self.isc = c.isc_gain * c.ilim
        self.c_x = 2 * v('n7002_ciss') + 20e-12

    # ---------------- sources ----------------
    def vset(self, t):
        pts = self.c.vset
        if len(pts) == 1 or t <= pts[0][0]:
            return pts[0][1]
        for (t0, v0), (t1, v1) in itertools.pairwise(pts):
            if t <= t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        return pts[-1][1]

    def g_short(self, t, L=None):
        c = self.c
        if not (L or self.L).short or t < c.t_fault:
            return 0.0
        return min(1.0, (t - c.t_fault) / c.t_edge) / c.r_short

    # ---------------- device currents ----------------
    def i_fet(self, x, L=None):
        L = L or self.L
        c = self.c
        vin, vout = x[IX['v_in']], x[IX['v_out']]
        dv = vin - vout
        if L.ef == 'on':
            return max(0.0, dv) / c.ron
        if L.ef == 'cl':
            return min(c.ilim, max(0.0, dv) / c.ron)
        if L.ef == 'start':
            return min(c.ilim, max(0.0, dv) / c.ron, max(0.0, 50.0 * (x[IX['v_ramp']] - vout)))
        return c.i_leak if dv > 0.5 else 0.0

    def v_aux(self, x, L=None):
        L = L or self.L
        c = self.c
        if not L.aux:
            return c.vaux_ol
        ra, rb = c.r_a
        return x[IX['v_out']] * (rb / (ra + rb) if c.iface == 'corrected' else 1.0)

    def v_mr(self, x):
        c = self.c
        if c.iface != 'corrected':
            return x[IX['v_out']]
        vgs = x[IX['v_x']]
        if vgs <= c.vth_n:
            return x[IX['v_out']]
        r = c.rds_n * (5.0 - c.vth_n) / (vgs - c.vth_n)
        return x[IX['v_out']] * r / (r + v('rmr'))

    def i_psink(self, x, L=None):
        """Current pulled out of P by the AUXOFF interface FET (Q_C or the proposal's BSS84)."""
        L = L or self.L
        c = self.c
        vp = x[IX['v_p']]
        if c.iface == 'corrected':
            return nmos_i(x[IX['v_x']], vp, c.vth_n, c.rds_n)
        if c.iface == 'bss84':      # source = P, drain = GND, gate = AUXOFF
            return nmos_i(vp - self.v_aux(x, L), vp, c.vth_p, c.rds_p)
        return 0.0

    def currents(self, t, x, L=None):
        L = L or self.L
        c = self.c
        vs, _il, vvin, vldo, vin, vout, vvcb, vp, vsh, _, vx = x
        i_int = max(-c.i_sink, (self.vset(t) - vs) / c.r_int)
        if t >= c.t_fault + c.t_cc:
            i_int = min(i_int, c.i_cc)
        i_ldo = 0.0
        en_ldo = min(1.0, max(0.0, (vvin - 2.3) / 0.2))      # smooth enable around the 2.4 V minimum input
        if en_ldo > 0:
            i_ldo = en_ldo * max(0.0, min(c.icl, c.gm_ldo * (c.vldo - vldo), (vvin - vldo) / c.r_do))
        i_s = self.g_short(t, L) * (vvin - vldo)
        i_div = vldo / sum(c.r_ov) + vldo / sum(c.r_en)
        i_rin = (vldo - vin) / c.r_in
        i_f = self.i_fet(x, L)
        iq = v('iq_on') * min(1.0, max(0.0, vin / 2.5))
        i_il = c.i_il * min(1.0, max(vout, 0.0) / 1.0)
        i_vcb = v('i_vcb') * min(1.0, max(vvcb, 0.0) / 1.0)
        i_aux_pu = vout / sum(c.r_a) if c.iface == 'corrected' else 0.0
        i_qa = nmos_i(self.v_aux(x, L), vx, c.vth_n, c.rds_n) if c.iface == 'corrected' else 0.0
        i_rx = (vout - vx) / c.r_x if c.iface == 'corrected' else 0.0
        i_u3 = vp / 50.0 if L.u3_reset else 0.0
        i_ps = self.i_psink(x, L)
        i_sd = vsh / v('r_sd') if L.cd else 0.0
        i_shsrc = max(0.0, 2.48 - vsh) * v('i_shdn') / 2.48   # Thevenin: V(SHDN) oc 2.48 V min, 10 uA at 0 V
        return {'i_int': i_int, 'i_ldo': i_ldo, 'i_s': i_s, 'i_div': i_div, 'i_rin': i_rin, 'i_f': i_f, 'iq': iq, 'i_il': i_il,
                    'i_vcb': i_vcb, 'i_aux_pu': i_aux_pu, 'i_qa': i_qa, 'i_rx': i_rx, 'i_u3': i_u3, 'i_ps': i_ps, 'i_sd': i_sd,
                    'i_shsrc': i_shsrc}

    def rhs(self, t, x):
        c = self.c
        k = self.currents(t, x)
        vs, il, vvin, _vldo, _vin, vout, vvcb, vp, vsh, _vr, _vx = x
        d = np.zeros(len(NS))
        d[0] = (k['i_int'] - il) / c.c_src
        d[1] = (vs - vvin - c.r_cab * il) / c.l_cab
        d[2] = (il - k['i_ldo'] - k['i_s']) / c.c1
        d[3] = (k['i_ldo'] + k['i_s'] - k['i_div'] - k['i_rin']) / c.c2
        d[4] = (k['i_rin'] - k['i_f'] - k['iq']) / c.c_in
        i_vcb_in = (vout - vvcb) / v('r1_vcb')
        d[5] = (k['i_f'] - k['i_il'] - (vout - vp) / v('r2_pu') - i_vcb_in - k['i_aux_pu'] - k['i_rx']) / c.c_out
        d[6] = (i_vcb_in - k['i_vcb']) / c.c5
        d[7] = ((vout - vp) / v('r2_pu') - k['i_u3'] - k['i_ps'] - (vp - vsh) / v('r52')) / v('c11_p')
        d[8] = ((vp - vsh) / v('r52') - vsh / v('r53') + k['i_shsrc'] - k['i_sd']) / v('c25')
        d[9] = c.sr if self.L.ef == 'start' else 0.0
        d[10] = (k['i_rx'] - k['i_qa']) / self.c_x if c.iface == 'corrected' else 0.0
        return d

    # ---------------- scheduling ----------------
    def sched(self, t, action, tok=None):
        self.seq += 1
        heapq.heappush(self.q, (t, self.seq, action, tok))

    def note(self, t, s):
        self.log.append((t, s))

    def u3_update(self, t):
        L = self.L
        if L.u3 and not L.u3_reset:
            L.u3_reset = True
            self.note(t, f'U3 RESET asserted ({",".join(sorted(L.u3))})')
        elif not L.u3 and L.u3_reset:
            L.tok += 1
            self.sched(t + self.c.td, 'u3_release', L.tok)

    # ---------------- event functions (rebuilt for the current logic state) ----------------
    def events(self):
        c, L = self.c, self.L
        ev = []

        def mk(fn, direction, name):
            fn.terminal, fn.direction, fn.name = True, direction, name
            ev.append(fn)
        mk(lambda t, x: x[3] * self.k_ov - (self.vov_f if L.ovlo else self.vov_r), -1 if L.ovlo else 1, 'ovlo')
        mk(lambda t, x: min(x[3] * self.k_en - (self.vuvlo_f if L.uv_ok else self.vuvlo_r),
                            x[4] - (self.vuvp_f if L.uv_ok else self.vuvp_r)), -1 if L.uv_ok else 1, 'uv')
        if c.ft_enabled and L.ef in ('on', 'cl') and not L.ft_off:
            mk(lambda t, x: self.i_fet(x) - self.isc, 1, 'ft')
        if L.ef in ('start', 'cl'):
            mk(lambda t, x: x[5] - (x[4] - 0.05), 1, 'started')
        # U3: UV / OV at 5 % overdrive (tPD condition); release at threshold + min hysteresis
        uv_set, ov_set = c.u3_uv * (1 - c.u3_od), c.u3_ov * (1 + c.u3_od)
        hy = v('u3_hys', 0)
        mk(lambda t, x: x[5] - (c.u3_uv * (1 + hy) if 'uv' in L.u3 or 'uv' in L.u3_pend else uv_set),
           1 if ('uv' in L.u3 or 'uv' in L.u3_pend) else -1, 'u3uv')
        mk(lambda t, x: x[5] - (c.u3_ov * (1 - hy) if 'ov' in L.u3 or 'ov' in L.u3_pend else ov_set),
           -1 if ('ov' in L.u3 or 'ov' in L.u3_pend) else 1, 'u3ov')
        mk(lambda t, x: x[5] - v('u3_uvlo', 1), 1 if 'uvlo' in L.u3 else -1, 'u3uvlo')
        if c.iface == 'corrected':
            mk(lambda t, x: self.v_mr(x) - v('vmr_l'), 1 if L.mr_low else -1, 'mr')
        k_cd = v('cd_k')
        mk(lambda t, x: x[7] - k_cd * x[6] - (1e-3 if L.cd_cmd else 0.0), 1 if L.cd_cmd else -1, 'cd')
        mk(lambda t, x: x[8] - (v('v_shutf') if L.u10_shdn_ok else v('v_shutr')), -1 if L.u10_shdn_ok else 1, 'shdn')
        mk(lambda t, x: x[5] - (v('u10_uvlo_off') if L.u10_uv_ok else 4.36), -1 if L.u10_uv_ok else 1, 'u10uv')
        return ev

    def on_event(self, name, t, x):
        c, L = self.c, self.L
        if name == 'ovlo':
            L.ovlo = not L.ovlo
            if L.ovlo:
                self.note(t, 'OVLO comparator trips')
                self.sched(t + c.t_ovlo, 'ovlo_off')
                self.sched(t + c.t_aux, 'aux_low')
            else:
                self.note(t, 'OVLO comparator releases')
                self.sched(t + c.t_swov, 'ovlo_release')
        elif name == 'uv':
            L.uv_ok = not L.uv_ok
            self.note(t, f'eFuse UV {"cleared" if L.uv_ok else "asserted"}')
            if not L.uv_ok:
                L.ef, L.aux = 'off', False
            else:
                self.sched(t + 0.5e-3, 'start')
        elif name == 'ft':
            self.note(t, 'fast-trip comparator trips')
            L.ft_off = True
            self.sched(t + c.t_sc, 'ft_off')
        elif name == 'started':
            L.ef = 'on'
            if L.uv_ok and not L.ovlo:
                L.aux = True
            self.note(t, 'eFuse fully on, AUXOFF released')
        elif name == 'u3uv':
            if 'uv' in L.u3 or 'uv' in L.u3_pend:
                L.u3.discard('uv'); L.u3_pend.discard('uv')
                self.u3_update(t)
            else:
                L.u3_pend.add('uv'); self.sched(t + c.tpd, 'u3_set', 'uv')
        elif name == 'u3ov':
            if 'ov' in L.u3 or 'ov' in L.u3_pend:
                L.u3.discard('ov'); L.u3_pend.discard('ov')
                self.u3_update(t)
            else:
                L.u3_pend.add('ov'); self.sched(t + c.tpd, 'u3_set', 'ov')
        elif name == 'u3uvlo':
            if 'uvlo' in L.u3:
                L.u3.discard('uvlo')
            else:
                L.u3.add('uvlo')
            self.u3_update(t)
        elif name == 'mr':
            L.mr_low = not L.mr_low
            self.note(t, f'MR {"low" if L.mr_low else "released"}')
            if L.mr_low:
                self.sched(t + c.tpd_mr, 'u3_set', 'mr')
            else:
                L.u3.discard('mr'); self.u3_update(t)
        elif name == 'cd':
            L.cd_cmd = not L.cd_cmd
            self.sched(t + v('tpd_tlv320x'), 'cd_set', L.cd_cmd)
        elif name in ('shdn', 'u10uv'):
            if name == 'shdn':
                L.u10_shdn_ok = not L.u10_shdn_ok
                self.note(t, 'SHDN_c > V(SHUTR) max' if L.u10_shdn_ok else 'SHDN_c < V(SHUTF)')
            else:
                L.u10_uv_ok = not L.u10_uv_ok
                self.note(t, f'U10 UVLO {"cleared (+5V_IL > 4.36 V)" if L.u10_uv_ok else "(+5V_IL < 3.88 V): FET off"}')
            on = L.u10_shdn_ok and L.u10_uv_ok
            if L.u10_on and not on:
                self.sched(t + v('tsd_1663'), 'u10_off')
            elif on and not L.u10_on:
                self.note(t, 'U10 enable: PA supply restart begins')
            L.u10_on = on

    def on_action(self, t, action, tok):
        c, L = self.c, self.L
        if action == 'ovlo_off' and L.ovlo:
            L.ovlo_off, L.ef = True, 'off'
            self.note(t, 'eFuse FET off (OVLO)')
        elif action == 'aux_low' and L.ovlo:
            L.aux = False
            self.note(t, 'AUXOFF pulled low')
        elif action == 'ovlo_release' and not L.ovlo:
            L.ovlo_off = False
            if L.uv_ok and not L.ft_off:
                L.ef = 'cl'
                self.note(t, 'eFuse restarts after OVLO (current-limited, dVdt bypassed)')
        elif action == 'ft_off' and L.ft_off:
            if L.ef in ('on', 'cl'):
                L.ef = 'off'
                self.note(t, 'eFuse FET off (fast-trip)')
            self.sched(t + c.t_deglitch, 'ft_retry')
        elif action == 'ft_retry':
            L.ft_off = False
            if L.uv_ok and not L.ovlo_off and not L.ovlo:
                L.ef = 'cl'
                self.note(t, 'eFuse retries after fast-trip (current-limited)')
        elif action == 'start' and L.uv_ok and L.ef == 'off' and not L.ovlo:
            L.ef = 'start'
            self.note(t, 'eFuse slew-controlled start')
        elif action == 'u3_set':
            if tok in L.u3_pend or tok == 'mr' and L.mr_low:
                L.u3_pend.discard(tok); L.u3.add(tok)
                self.u3_update(t)
        elif action == 'u3_release' and tok == L.tok and not L.u3:
            L.u3_reset = False
            self.note(t, 'U3 RESET released (tD elapsed)')
        elif action == 'cd_set':
            L.cd = tok
            self.note(t, f'CD {"fires: Q_sd on" if tok else "released"}')
        elif action == 'u10_off':
            self.note(t, 'U10 FET off (tSD max after SHDN_c < 0.8 V)')
        elif action == 'fault':
            L.short = True
            self.note(t, 'U1 pass-element short begins')
        elif action == 'clear':
            L.short = False
            self.note(t, 'U1 short removed')

    # ---------------- run ----------------
    def x0(self):
        c = self.c
        if c.init == 'off':
            self.L = Logic(ef='off', uv_ok=False, aux=False, u3={'uvlo', 'uv'}, u3_reset=True, u10_on=False,
                           u10_shdn_ok=False, u10_uv_ok=False)
            return np.zeros(len(NS))
        vs = self.vset(0.0)
        vldo = c.vldo
        vin = vldo - (c.i_il + 3e-3) * c.r_in
        vout = vin - (c.i_il + 3e-3) * c.ron
        vp = vout * 94e3 / 96.2e3
        x = [vs, 0.0, vs, vldo, vin, vout, vout - 0.15, vp, vp / 2, vout, 0.0]
        return np.array(x, float)

    def run(self):
        c = self.c
        x = self.x0()
        t = 0.0
        if c.t_fault < math.inf:
            self.sched(c.t_fault, 'fault')
            if c.t_clear < math.inf:
                self.sched(c.t_fault + c.t_clear, 'clear')
        # breakpoints of the source waveform and the short ramp
        for tb, _ in c.vset:
            if tb > 0:
                self.sched(tb, 'bp')
        if c.t_fault < math.inf:
            self.sched(c.t_fault + c.t_edge, 'bp')
            if c.t_cc > 0:
                self.sched(c.t_fault + c.t_cc, 'bp')
        guard = 0
        while t < c.t_end and guard < 20000:
            guard += 1
            t_next = min(self.q[0][0] if self.q else c.t_end, c.t_end)
            if t_next > t:
                fast = (c.t_fault <= t + 1e-15 < c.t_fault + c.fast_window) or \
                       (c.t_fault + c.t_clear <= t < c.t_fault + c.t_clear + c.fast_window)
                ms = c.max_step_fast if fast else c.max_step_slow
                if c.t_fault < math.inf and t < c.t_fault < t_next:
                    t_next = c.t_fault
                evs = [e for e in self.events() if e is not None]
                sol = solve_ivp(self.rhs, (t, t_next), x, method='LSODA', events=evs, max_step=ms,
                                rtol=1e-6, atol=1e-9)
                self.segs.append((sol.t, sol.y, replace(self.L, u3=set(self.L.u3), u3_pend=set(self.L.u3_pend))))
                x, t = sol.y[:, -1].copy(), sol.t[-1]
                hit = [(te[0], e.name) for te, e in zip(sol.t_events, evs) if len(te)]
                if sol.status == 1 and hit:
                    for _, name in sorted(hit)[:1]:
                        self.on_event(name, t, x)
                    continue
            while self.q and self.q[0][0] <= t + 1e-15:
                _, _, action, tok = heapq.heappop(self.q)
                self.on_action(t, action, tok)
            if not self.q and t >= c.t_end:
                break
        return self

    # ---------------- post-processing ----------------
    def trace(self):
        ts = np.concatenate([s[0] for s in self.segs])
        ys = np.concatenate([s[1] for s in self.segs], axis=1)
        return ts, ys

    def series(self):
        """Arrays incl. derived currents/powers, evaluated with the logic state of each segment."""
        out = {k: [] for k in ('t', *NS, 'i_f', 'i_rin', 'i_s', 'i_ps', 'p_fet', 'p_rin', 'p_s', 'p_ps', 'v_aux',
                               'v_mr', 'v_ovlo', 'v_en')}
        for ts, ys, L in self.segs:
            for j, t in enumerate(ts):
                x = ys[:, j]
                k = self.currents(t, x, L)
                out['t'].append(t)
                for n in NS:
                    out[n].append(x[IX[n]])
                out['i_f'].append(k['i_f']); out['i_rin'].append(k['i_rin']); out['i_s'].append(k['i_s'])
                out['i_ps'].append(k['i_ps'])
                out['p_fet'].append(k['i_f'] * (x[4] - x[5]))
                out['p_rin'].append(k['i_rin'] ** 2 * self.c.r_in)
                out['p_s'].append(k['i_s'] * (x[2] - x[3]))
                out['p_ps'].append(k['i_ps'] * x[7])
                out['v_aux'].append(self.v_aux(x, L)); out['v_mr'].append(self.v_mr(x))
                out['v_ovlo'].append(x[3] * self.k_ov); out['v_en'].append(x[3] * self.k_en)
        return {k: np.asarray(a) for k, a in out.items()}

    def first(self, text, after=0.0):
        for t, s in self.log:
            if t >= after and text in s:
                return t
        return math.nan
