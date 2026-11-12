* h2c_plant.inc -- OpenRU H2-C power tree + PA-drain interlock. BEHAVIOURAL / PRELIMINARY (datasheet timing),
* not hardware-validated. No vendor models: every IC is a B-source / switch / ramp built from datasheet numbers.
* Sources of every number: H2C_SEQUENCING_SIM.md ("Parameters", "Revision 2").
* Units: s, V, A, ohm. "tm_*" nodes are integrators reading in ms since the block was enabled (1 V = 1 ms).
*
* Revision 2 hardware (schematic): U915 74LVC1G08 IL_EN = NEG_RAILS_OK . PG_3V3RF (100k pull-down) drives the
*   TPS22917 ON pin and U912 input A (NEG_OK = IL_EN . GATES_OK). PGOOD per SLVSEY5C 7.3.4.
* Revision 2 candidates (selected by .param, default = current schematic):
*   cb_en      drain crowbar per chain (N-MOSFET + series R on +5V_PA_C1, gate pulled up from +5V_PA, held off by
*              a small N-MOSFET Q2 driven from PA_DRAIN_EN through an RC break-before-make delay)
*   ilref_mode 0: TPS22917 VIN = +1V8_DIG (schematic)   1: VIN = TLV75518P LDO from +3V3_RF, EN tied to IN
*              2: same LDO but LDO EN = PG_3V3RF
*   sup_en     dual supervisor (VDD = +3V3_RF/+5V_PA diode-OR, valid >= 0.9 V, sense +1V8_DIG 1.67 V / +3V3_AUX 2.97 V, tRST), open-drain
*              RESET_N on the PG_3V3RF net; BAT54C from PG_3V3RF clamps PA_DRAIN_EN and IL_CLR_N
*   pess       1 = pessimistic logic: LM339B with VS < 2 V floats (always), LVC (VCC < lvc_vmin) outputs HIGH (= VCC)
*              and the flop is SET; LVC / TPS22917 / TLV755 inputs read HIGH above VIL, TPS22810 EN on above 1.08 V
*   free       1 = "free rail" mode for ordering tests: +3V3_AUX, +1V8_DIG, +3V3_RF, +5V_PA, -5V_BF, -3V3_SW are
*              independent sourcing-only ramps commanded by fr_aux fr_18 fr_rf fr_pa fr_n5 fr_n3 (0/1)
*   adar_reset 1 = ADAR1000 PA_BIAS registers read 0 V unless AVDD3 has been up continuously since the last
*              firmware write (node tlw = time of last write, s)
*
* Stimulus nodes a scenario must drive: vin ; fw_en3v3 fw_en5vpa fw_enneg fw_pa_en fw_wdt (0/1) ; dac1..dac4 (V) ;
*   ldo5_kill rf_kill (0/1) ; tlw (s) ; fr_aux fr_18 fr_rf fr_pa fr_n5 fr_n3 (0/1, only read when free=1)

.param rpd=400 lvc_vmin=1.65 pess=0 free=0 adar_reset=0 adar_vmin=2.8
.param cb_en=0 cb_r=0.38 cb_rpu=4.7k cb_vth=1.5 cb_ciss=1n q2_vth=0.75 q2_r=10k q2_c=1n tsw_off=3.3u
.param asb=0 q3_cg=100p sup_tdet=0.1u fetclamp=0
.param ilref_mode=0 sup_en=0 sup_vth=1.67 sup_aux=2.97 sup_vpor=0.9 sup_trst=10
.param cvout=19.81u rf_uv=0 gclamp=0 cref=100n
.param tr_aux=1 tr_18=0.5 tr_rf=1 tr_pa=1 tr_n5=2 tr_n3=2
* LVC input threshold: VCC/2 nominal, VIL (0.35 VCC) when pessimistic
.param kth={0.5-0.15*pess}

* ---------- generic models ----------
.model swoc   sw vt=0.5 vh=0.1  ron=30  roff=1e10
.model dgate  d  is=1e-12 n=1.5
.func clip01(x) {min(1, max(0, x))}
* ADTR1107 PA drain current vs gate (ASSUMPTION, piecewise linear):
*   0 A at <= -1.75 V, 0.22 A at -1.1 V (ADTR1107/ADAR1000 p45), 0.6 A at 0 V (pessimistic assumption)
.func idss(vg) {vg < -1.75 ? 0 : (vg < -1.1 ? 0.22*(vg+1.75)/0.65 : 0.22 + 0.34545*(min(vg,0.6)+1.1))}
* LVC output: logic when VCC valid; otherwise LOW (nominal) or VCC (pessimistic)
.func lvc(v, x) {v >= lvc_vmin ? (x > 0.5 ? v : 0) : (pess > 0.5 ? v : 0)}

* =============================== power tree ===============================
* --- U652 TPS62933 -> +3V3_AUX. UVLO divider start 8 V / stop 7 V, tSS 4.8 ms, COUT 3x22u ---
Baux_en  aux_en 0 V = V(vin) > (V(aux_en_f) > 0.5 ? 7 : 8) ? 1 : 0
Raux_en  aux_en aux_en_f 1k
Caux_en  aux_en_f 0 1n
Btm_aux  0 tm_aux I = V(aux_en) > 0.5 ? 1m : -V(tm_aux)
Ctm_aux  tm_aux 0 1u
Baux     0 aux I = {free} > 0.5 ? 0 : (V(aux_en) > 0.5 ? max(0, min(3.328*clip01(V(tm_aux)/4.8), V(vin)-0.5) - V(aux))/0.01 : 0)
Caux     aux 0 66u
* AUX loads: telemetry/comparators 0.2 A (fades below 1 V); +1V8 LDO and TPS65131 input added below
Baux_ld  aux 0 I = 0.2*clip01(V(aux))

* --- U653 TLV75518P -> +1V8_DIG. UVLO 1.30 V rising / 1.26 V falling, tSTR 0.55 ms, 120 ohm pull-down when off ---
B18_en   v18_en 0 V = V(aux) > (V(v18_en_f) > 0.5 ? 1.26 : 1.30) ? 1 : 0
R18_en   v18_en v18_en_f 1k
C18_en   v18_en_f 0 1n
Btm_18   0 tm_18 I = V(v18_en) > 0.5 ? 1m : -V(tm_18)
Ctm_18   tm_18 0 1u
B18      aux v18 I = {free} > 0.5 ? 0 : (V(v18_en) > 0.5 ? max(0, min(1.8*clip01(V(tm_18)/0.55), V(aux)-0.15) - V(v18))/0.001 : 0)
B18_pd   v18 0 I = ({free} < 0.5 && V(v18_en) < 0.5) ? V(v18)/120 : 0
C18      v18 0 8.4u
* +1V8_DIG load 150 mA max (resistive)
R18_ld   v18 0 12

* --- free-rail mode: independent sourcing-only ramps (ordering tests). No discharge: rails decay into their loads ---
Btm_fa  0 tm_fa I = V(fr_aux) > 0.5 ? 1m : -V(tm_fa)
Ctm_fa  tm_fa 0 1u
Bfa     0 aux  I = ({free} > 0.5 && V(fr_aux) > 0.5) ? max(0, 3.328*clip01(V(tm_fa)/{tr_aux}) - V(aux))/0.01 : 0
Btm_f18 0 tm_f18 I = V(fr_18) > 0.5 ? 1m : -V(tm_f18)
Ctm_f18 tm_f18 0 1u
* +1V8_DIG is an LDO on +3V3_AUX even in free mode (cannot exceed +3V3_AUX - 0.15 V)
Bf18    aux v18  I = ({free} > 0.5 && V(fr_18) > 0.5) ? max(0, min(1.8*clip01(V(tm_f18)/{tr_18}), V(aux)-0.15) - V(v18))/0.001 : 0
Btm_frf 0 tm_frf I = V(fr_rf) > 0.5 ? 1m : -V(tm_frf)
Ctm_frf tm_frf 0 1u
Bfrf    0 v3rf I = ({free} > 0.5 && V(fr_rf) > 0.5) ? max(0, 3.327*clip01(V(tm_frf)/{tr_rf}) - V(v3rf))/0.01 : 0
Btm_fpa 0 tm_fpa I = V(fr_pa) > 0.5 ? 1m : -V(tm_fpa)
Ctm_fpa tm_fpa 0 1u
Bfpa    0 v5pa I = ({free} > 0.5 && V(fr_pa) > 0.5) ? max(0, 5.0*clip01(V(tm_fpa)/{tr_pa}) - V(v5pa))/0.01 : 0
Btm_fn5 0 tm_fn5 I = V(fr_n5) > 0.5 ? 1m : -V(tm_fn5)
Ctm_fn5 tm_fn5 0 1u
Bfn5    n5v 0 I = ({free} > 0.5 && V(fr_n5) > 0.5) ? max(0, V(n5v) + 4.999*clip01(V(tm_fn5)/{tr_n5}))/0.02 : 0
Btm_fn3 0 tm_fn3 I = V(fr_n3) > 0.5 ? 1m : -V(tm_fn3)
Ctm_fn3 tm_fn3 0 1u
Bfn3    n3v3 0 I = ({free} > 0.5 && V(fr_n3) > 0.5) ? max(0, V(n3v3) + 3.311*clip01(V(tm_fn3)/{tr_n3}))/0.02 : 0

* --- MCU (STM32, on +1V8_DIG). GPIO valid only above 1.65 V (ASSUMPTION ~ PDR: reset, Hi-Z, 100k pull-downs) ---
Bpe3     pwr_en_3v3  0 V = (V(v18) > 1.65 && V(fw_en3v3)  > 0.5) ? V(v18) : 0
Bpe5     pwr_en_5vpa 0 V = (V(v18) > 1.65 && V(fw_en5vpa) > 0.5) ? V(v18) : 0
Bpen     pwr_en_neg  0 V = (V(v18) > 1.65 && V(fw_enneg)  > 0.5) ? V(v18) : 0
Bpaen    mcu_pa_en   0 V = (V(v18) > 1.65 && V(fw_pa_en)  > 0.5) ? V(v18) : 0
* TPS3430 WDO open-drain, pulled up to +1V8_DIG (assumed); WDT_OK follows firmware health bit
Bwdt     wdt_ok      0 V = (V(v18) > 1.65 && V(fw_wdt)    > 0.5) ? V(v18) : 0

* --- U650 TPS568230 -> +3V3_RF_SRC (= ADAR1000 AVDD3, ADTR1107 VDD_SW). EN > 1.31 V, UVLO 3.8 V,
*     0.6 ms MODE read + 2.64 ms SS, 420 ohm discharge when off. COUT 4x47u, load 4 A. In free mode EN = fr_rf ---
Brf_en   rf_en 0 V = ({free} > 0.5 ? V(fr_rf) > 0.5 : (V(pwr_en_3v3) > 1.31 && V(vin) > 3.8)) ? 1 : 0
Btm_rf   0 tm_rf I = V(rf_en) > 0.5 ? 1m : -V(tm_rf)
Ctm_rf   tm_rf 0 1u
Brf      0 v3rf I = {free} > 0.5 ? 0 : (V(rf_en) > 0.5 ? (V(rf_kill) > 0.5 ? 0 : 1)*max(0, min(3.327*clip01((V(tm_rf)-0.6)/2.64), V(vin)-0.3) - V(v3rf))/0.01 : V(v3rf)/(-420))
Crf      v3rf 0 188u
Rrf_ld   v3rf 0 0.832
* PGOOD (open drain, 100k to +1V8_DIG), SLVSEY5C 7.3.4: low while EN low, during soft-start, FB < 85 % or > 115 %
* (UVP/OVP/OTP shown as UV here); released 1 ms after FB is inside 90..110 %. pg_tm = ms spent inside the window
* (held inside the 85..90 / 110..115 % band, reset outside it). Soft-start = 3.24 ms after EN (0.6 ms in free mode).
* The open drain can sink only while the TPS568230 internal supply exists: VIN > 1.5 V (ASSUMPTION).
Bpgtm    0 pg_tm I = (V(rf_en) > 0.5 && V(tm_rf) > ({free} > 0.5 ? 0.6 : 3.24) && V(v3rf) > 0.9*3.327 && V(v3rf) < 1.1*3.327) ? 1m : ((V(rf_en) < 0.5 || V(v3rf) < 0.85*3.327 || V(v3rf) > 1.15*3.327) ? -V(pg_tm) : 0)
Cpgtm    pg_tm 0 1u
* PG_3V3RF is a real open-drain net: R654 100k to +1V8_DIG; U650 PGOOD sinks (VOL <= 0.4 V at 4 mA -> 100 ohm,
* pessimistic linearisation) while not good and VIN > 1.5 V; the supervisor RESET_N sinks in parallel (see below).
Bpgok    pg_good 0 V = (V(rf_en) > 0.5 && V(pg_tm) > 1.0 && V(v3rf) > 0.85*3.327 && V(v3rf) < 1.15*3.327) ? 1 : 0
Bpgsnk   pg_tsink 0 V = (V(pg_good) < 0.5 && V(vin) > 1.5) ? 1 : 0
R654     v18 pg_3v3rf 100k
Bpg_t    pg_3v3rf 0 I = V(pg_tsink) > 0.5 ? V(pg_3v3rf)/100 : 0
Bpg_s    pg_3v3rf 0 I = V(isup)
Cpg      pg_3v3rf 0 20p

* --- U651 TPS568230 -> +5V_PA (feeds the 4 TPS22810 drain switches). COUT 5x47u ---
Bpa_en   pa5_en 0 V = (V(pwr_en_5vpa) > 1.31 && V(vin) > 3.8) ? 1 : 0
Btm_pa   0 tm_pa I = V(pa5_en) > 0.5 ? 1m : -V(tm_pa)
Ctm_pa   tm_pa 0 1u
Bpa5     0 v5pa I = {free} > 0.5 ? 0 : (V(pa5_en) > 0.5 ? max(0, min(5.0*clip01((V(tm_pa)-0.6)/2.64), V(vin)-0.3) - V(v5pa))/0.01 : V(v5pa)/(-420))
Cpa5     v5pa 0 235u

* --- U913 74LVC1G08: ENN = PWR_EN_NEG . PG_3V3RF (amendment A2) ---
Benn     enn 0 V = lvc(V(v18), V(pwr_en_neg) > {kth}*V(v18) && V(pg_3v3rf) > {kth}*V(v18))

* --- U657 TPS65131 inverter -> PWR_VNEG -6.344 V. ENN VIH 1.4 V, UVLO 2.35 V typ, ~1 ms start-up,
*     output disconnected (high-Z) when off. eff 77 % for AUX input current. COUT 4x4.7u + 2x10u LDO CIN ---
Bneg_en  neg_en 0 V = ({free} < 0.5 && V(enn) > ({pess} > 0.5 ? 0.4 : 1.4) && V(aux) > 2.35) ? 1 : 0
Btm_neg  0 tm_neg I = V(neg_en) > 0.5 ? 1m : -V(tm_neg)
Ctm_neg  tm_neg 0 1u
Bneg     vneg 0 I = V(neg_en) > 0.5 ? max(0, V(vneg) + 6.344*clip01(V(tm_neg)/1.0))/0.05 : 0
Cneg     vneg 0 38.8u
Baux_neg aux 0 I = V(neg_en) > 0.5 ? (-V(vneg))*max(0, V(vneg) + 6.344*clip01(V(tm_neg)/1.0))/0.05/(0.77*max(V(aux),1)) : 0

* --- U658 TPS7A3301 -> -5V_BF (ADAR1000 AVDD1). EN tied to IN (|VEN| >= 2 V), SS 1.2 ms/nF x 100 nF = 120 ms,
*     dropout 0.2 V, no discharge. COUT 47u. ldo5_kill = abrupt disable ---
Bl5_en   l5_en 0 V = ({free} < 0.5 && V(vneg) < -2 && V(ldo5_kill) < 0.5) ? 1 : 0
Btm_l5   0 tm_l5 I = V(l5_en) > 0.5 ? 1m : -V(tm_l5)
Ctm_l5   tm_l5 0 1u
Bl5      n5v vneg I = V(l5_en) > 0.5 ? max(0, V(n5v) - max(-4.999*clip01(V(tm_l5)/120), V(vneg)+0.2))/0.02 : 0
Cn5      n5v 0 47u
* 4 x ADAR1000 AVDD1 at 50 mA each worst case (fades below 1 V)
Bn5_ld   0 n5v I = 0.2*clip01(-V(n5v))

* --- U659 TPS7A3301 -> -3V3_SW (ADTR1107 VSS_SW). Same SS. COUT 47u, load 5 mA ---
Bl3_en   l3_en 0 V = ({free} < 0.5 && V(vneg) < -2) ? 1 : 0
Btm_l3   0 tm_l3 I = V(l3_en) > 0.5 ? 1m : -V(tm_l3)
Ctm_l3   tm_l3 0 1u
Bl3      n3v3 vneg I = V(l3_en) > 0.5 ? max(0, V(n3v3) - max(-3.311*clip01(V(tm_l3)/120), V(vneg)+0.2))/0.02 : 0
Cn3      n3v3 0 47u
Bn3_ld   0 n3v3 I = 0.005*clip01(-V(n3v3))

* ============================ interlock ============================
* --- rail monitors on +1V8_DIG (INTERLOCK_SPEC 3.3/3.4) -> NEG_RAILS_OK ---
R948 v18  il_n5v 12.4k
R949 n5v  il_n5v 49.9k
R950 v18  il_n3v3 12.4k
R951 n3v3 il_n3v3 49.9k
R956 v18 il_ref_n5v 3.92k
R957 il_ref_n5v 0 1.62k
R958 v18 il_ref_n3v3 1.21k
R959 il_ref_n3v3 0 1.07k
R966 aux il_v33mon 46.4k
R967 il_v33mon 0 10.0k

* --- U915 74LVC1G08 (rev 2): IL_EN = NEG_RAILS_OK . PG_3V3RF ; 100k pull-down on output ---
Bilen    il_en_s 0 V = lvc(V(v18), V(neg_rails_ok) > {kth}*V(v18) && V(pg_3v3rf) > {kth}*V(v18))
Rilen    il_en_s il_en 50
R968     il_en 0 100k

* --- IL_REF source (ilref_mode): 0 = +1V8_DIG ; 1/2 = TLV75518P from +3V3_RF (UVLO 1.30/1.26 V, tSTR 0.55 ms,
*     120 ohm active pull-down when off, EN VHI 1.0 V; EN = IN (1) or EN = PG_3V3RF (2)), COUT 1 uF ---
Bls_en   ls_en 0 V = (V(v3rf) > (V(ls_en_f) > 0.5 ? 1.26 : 1.30) && ({ilref_mode} < 1.5 || V(pg_3v3rf) > ({pess} > 0.5 ? 0.3 : 0.65))) ? 1 : 0
Rls_en   ls_en ls_en_f 1k
Cls_en   ls_en_f 0 1n
Btm_ls   0 tm_ls I = V(ls_en) > 0.5 ? 1m : -V(tm_ls)
Ctm_ls   tm_ls 0 1u
Bls      v3rf ilsrc I = ({ilref_mode} > 0.5 && V(ls_en) > 0.5) ? max(0, min(1.8*clip01(V(tm_ls)/0.55), V(v3rf)-0.15) - V(ilsrc))/0.01 : 0
Bls_pd   ilsrc 0 I = ({ilref_mode} > 0.5 && V(ls_en) > 0.5) ? 0 : V(ilsrc)/120
Cls      ilsrc 0 1u

* --- U914 TPS22917 IL_REF switch, ON = IL_EN (VIH 1 V / VIL 0.35 V; nominal threshold = midpoint 0.675 V,
*     pessimistic 0.35 V), VIN 1.8 V CT open: tON 200 us = ~100 us delay + tR 100 us, tOFF 10 us, QOD 150 ohm
*     (QOD tied to VOUT, assumed); output limited to its VIN ---
* sup_en: supervisor active-high push-pull RESET (same VDD) drives an N-MOSFET Q3 that clamps the TPS22917 ON pin
*         (10k series from U915) to GND while the supervisor is asserted
* as built (asb=1): Q3 (DMG1012T) gate = IL_Q3G = inverter Q966 (gate PG_3V3RF, 100k R976 to supervisor VDD)
Bref_en  ref_en 0 V = (V(il_en) > ({pess} > 0.5 ? 0.35 : 0.675) && !({sup_en} > 0.5 && ({asb} > 0.5 ? V(il_q3g) > {q2_vth} : V(sup_act) > 0.5))) ? 1 : 0
* fetclamp=1: R976 is fed from a diode-OR of the supervisor VDD and +1V8_DIG (extra BAT54), so IL_Q3G is high
*            whenever PG_3V3RF is low and any of +3V3_RF / +5V_PA / +1V8_DIG exists
Bq3pu    0 il_q3g I = {asb}*(({fetclamp} > 0.5 ? max(V(supvdd), V(v18)-0.24) : V(supvdd)) - V(il_q3g))/100k
Bq966    il_q3g 0 I = {asb}*clip01((V(pg_3v3rf)-{q2_vth})/0.3)*V(il_q3g)/0.7
Cq3g     il_q3g 0 {q3_cg}
Rlk4     il_q3g 0 1G
Tref     ref_en 0 ref_en_d 0 Z0=50 TD=10u
Rref_t   ref_en_d 0 50
Btm_ref  0 tm_ref I = V(ref_en_d) > 0.5 ? 1m : -V(tm_ref)
Ctm_ref  tm_ref 0 1u
Bref18   v18 il_ref I = ({ilref_mode} < 0.5 && V(ref_en_d) > 0.5) ? max(0, min(V(v18), 1.8*clip01((V(tm_ref)-0.0975)/0.125)) - V(il_ref))/0.12 : 0
Brefls   ilsrc il_ref I = ({ilref_mode} > 0.5 && V(ref_en_d) > 0.5) ? max(0, min(V(ilsrc), 1.8*clip01((V(tm_ref)-0.0975)/0.125)) - V(il_ref))/0.12 : 0
Bref_qod il_ref 0 I = V(ref_en_d) > 0.5 ? 0 : V(il_ref)/150
Cref     il_ref 0 {cref}
R952 il_ref il_ref_lost 2.15k
R953 il_ref_lost 0 2.74k
R954 il_ref il_ref_pinch 1.47k
R955 il_ref_pinch 0 1.02k

* --- chain 1: ADAR1000 PA_BIAS1..4 -> ADTR1107 VGG_PA (10 nF), gate dividers on IL_REF ---
* PA_BIAS = clip(REG, AVDD1, 0) behind 100 ohm (ASSUMPTION); high-Z while AVDD3 (+3V3_RF) < adar_vmin.
* adar_reset=1: REG = 0 V unless AVDD3 has been up continuously since the last firmware write (power-on reset, p41).
Btm_ad   0 tm_ad I = V(v3rf) > {adar_vmin} ? 1m : -V(tm_ad)
Ctm_ad   tm_ad 0 1u
Bregok   regok 0 V = ({adar_reset} < 0.5 || V(tm_ad)*1e-3 > time - V(tlw)) ? 1 : 0
Bdrv1 drv1 0 V = min(0, max(V(dac1)*V(regok), V(n5v)))
Bdrv2 drv2 0 V = min(0, max(V(dac2)*V(regok), V(n5v)))
Bdrv3 drv3 0 V = min(0, max(V(dac3)*V(regok), V(n5v)))
Bdrv4 drv4 0 V = min(0, max(V(dac4)*V(regok), V(n5v)))
Bg1 drv1 gate1 I = V(v3rf) > {adar_vmin} ? (V(drv1)-V(gate1))/100 : 0
Bg2 drv2 gate2 I = V(v3rf) > {adar_vmin} ? (V(drv2)-V(gate2))/100 : 0
Bg3 drv3 gate3 I = V(v3rf) > {adar_vmin} ? (V(drv3)-V(gate3))/100 : 0
Bg4 drv4 gate4 I = V(v3rf) > {adar_vmin} ? (V(drv4)-V(gate4))/100 : 0
Cg1 gate1 0 10n
Cg2 gate2 0 10n
Cg3 gate3 0 10n
Cg4 gate4 0 10n
Dg1 gate1 0 dgate
Dg2 gate2 0 dgate
Dg3 gate3 0 dgate
Dg4 gate4 0 dgate
* gclamp=1: per-gate Schottky clamp to GND (BAT54-class, Is 2e-7 A, n 1.05; candidate, INTERLOCK_SPEC R1(a))
Bgc1 gate1 0 I = {gclamp}*2e-7*(exp(min(V(gate1),1)/(1.05*0.02585))-1)
Bgc2 gate2 0 I = {gclamp}*2e-7*(exp(min(V(gate2),1)/(1.05*0.02585))-1)
Bgc3 gate3 0 I = {gclamp}*2e-7*(exp(min(V(gate3),1)/(1.05*0.02585))-1)
Bgc4 gate4 0 I = {gclamp}*2e-7*(exp(min(V(gate4),1)/(1.05*0.02585))-1)
R900 gate1 il_g1 49.9k
R901 il_ref il_g1 17.4k
R902 il_g1 0 45.3k
R903 gate2 il_g2 49.9k
R904 il_ref il_g2 17.4k
R905 il_g2 0 45.3k
R906 gate3 il_g3 49.9k
R907 il_ref il_g3 17.4k
R908 il_g3 0 45.3k
R909 gate4 il_g4 49.9k
R910 il_ref il_g4 17.4k
R911 il_g4 0 45.3k

* --- LM339B comparators (ideal, open collector), active only with +3V3_AUX > 2 V (VS min), floating below
*     (= HIGH via the pull-ups, i.e. pessimistic in both modes); response 1.3 us (LMx39 p12); 0.5 mV input offset
*     in the late-trip direction (inside LM339B VIO 5.5 mV; also avoids numerical chatter at equal inputs) ---
* rf_uv > 0: extra LM339B channel on NEG_RAILS_OK tripping when +3V3_RF < rf_uv (candidate)
Bfr  frail 0 V = ((V(il_n5v) > V(il_ref_n5v) + 0.5m) || (V(il_n3v3) > V(il_ref_n3v3) + 0.5m) || (V(il_ref_n5v) > V(il_v33mon) + 0.5m) || ({rf_uv} > 0 && V(v3rf) < {rf_uv})) && V(aux) > 2 ? 1 : 0
Bfg  fgate 0 V = ((V(il_g1) > V(il_ref_lost) + 0.5m) || (V(il_g2) > V(il_ref_lost) + 0.5m) || (V(il_g3) > V(il_ref_lost) + 0.5m) || (V(il_g4) > V(il_ref_lost) + 0.5m)) && V(aux) > 2 ? 1 : 0
Bfp  fpin  0 V = ((V(il_g1) > V(il_ref_pinch) + 0.5m) || (V(il_g2) > V(il_ref_pinch) + 0.5m) || (V(il_g3) > V(il_ref_pinch) + 0.5m) || (V(il_g4) > V(il_ref_pinch) + 0.5m)) && V(aux) > 2 ? 1 : 0
Tfr frail 0 frail_d 0 Z0=50 TD=1.3u
Rfr frail_d 0 50
Tfg fgate 0 fgate_d 0 Z0=50 TD=1.3u
Rfg fgate_d 0 50
Tfp fpin 0 fpin_d 0 Z0=50 TD=1.3u
Rfp fpin_d 0 50
Srail  neg_rails_ok  0 frail_d 0 swoc
Sgate  gates_ok      0 fgate_d 0 swoc
Spin   gates_pinched 0 fpin_d  0 swoc
Rpu1 aux neg_rails_ok 10k
Rpd1 neg_rails_ok 0 10k
Cn1  neg_rails_ok 0 50p
Rpu2 aux gates_ok 10k
Rpd2 gates_ok 0 10k
Cn2  gates_ok 0 50p
R962 aux gates_pinched 10k
R963 gates_pinched 0 10k
Cn3n gates_pinched 0 50p

* --- dual supervisor candidate (sup_en): VDD = +3V3_RF / +5V_PA diode-OR (BAT54C), SENSE1 = +1V8_DIG (sup_vth), SENSE2 = +3V3_AUX (sup_aux),
*     open-drain RESET_N wired onto the PG_3V3RF net (wired-AND with TPS568230 PGOOD), output valid for VDD >= sup_vpor,
*     asserted while either sense is low and for sup_trst ms after both are good.
*     BAT54C (anodes PA_DRAIN_EN / IL_CLR_N, cathode PG_3V3RF; 1k series at U705 / U911 outputs) clamp both nets to
*     PG_3V3RF + 0.35 V whenever that net is low. Below sup_vpor (VDD) the output is taken as not pulling ---
* detection (assert) delay sup_tdet as an ideal delay line on the "bad" condition (TPS386000: unspecified)
Bsbad    sbad 0 V = (V(v18) > {sup_vth} && V(aux) > {sup_aux}) ? 0 : 1
Tsup     sbad 0 sbad_d 0 Z0=50 TD={sup_tdet}
Rsup_t   sbad_d 0 50
Btm_sup  0 tm_sup I = V(sbad_d) < 0.5 ? 1m : -V(tm_sup)
* supervisor VDD = BAT54C diode-OR of +3V3_RF and +5V_PA (VF ~0.24 V at uA)
Bsvdd    supvdd 0 V = max(0, max(V(v3rf), V(v5pa)) - 0.24)
Ctm_sup  tm_sup 0 1u
Bsup     sup_act 0 V = ({sup_en} > 0.5 && V(supvdd) > {sup_vpor} && V(tm_sup) < {sup_trst}) ? 1 : 0
* RESET_N sink, pessimistic linearised VOL (SBVS105F 6.5): VDD >= 1.8 V: 0.4 V at 1 mA (400 ohm);
* 1.3..1.8 V: 0.3 V at 0.4 mA (750 ohm); 0.9..1.3 V: 0.2 V at 15 uA (13.3 kohm). Current exposed as node isup (A).
Bisup    isup 0 V = V(sup_act) > 0.5 ? V(pg_3v3rf)/(V(supvdd) >= 1.8 ? 400 : (V(supvdd) >= 1.3 ? 750 : 13.3k)) : 0

* --- 1.8 V logic (LVC: inputs compare to kth*VCC; outputs per lvc()) ---
* U912 74LVC1G08 (rev 2): NEG_OK = IL_EN . GATES_OK
Bnegok neg_ok 0 V = lvc(V(v18), V(il_en) > {kth}*V(v18) && V(gates_ok) > {kth}*V(v18))
* U911 74LVC1G11: IL_CLR_N = MCU_PA_EN . WDT_OK . NEG_OK (1k series, supervisor clamp)
Bclr il_clr_s 0 V = lvc(V(v18), V(mcu_pa_en) > {kth}*V(v18) && V(wdt_ok) > {kth}*V(v18) && V(neg_ok) > {kth}*V(v18))
Rclr il_clr_s il_clr_n 1k
* BAT54C (DS11005 VF max 0.24 V @0.1 mA, 0.32 V @1 mA, 0.40 V @10 mA -> Is 9.9e-8, n*Vt 34.7 mV), anode net -> PG
Dclr   il_clr_n dk1 dbat54
Rclr_d dk1 pg_3v3rf {1e12-sup_en*(1-fetclamp)*(1e12-0.5)}
.model dbat54 d is=9.9e-8 n=1.343 rs=0
* R964 10k / C912 1nF -> U910 74LVC1G17 (VT+ ~0.95 V)
R964 mcu_pa_en il_clk_rc 10k
C912 il_clk_rc 0 1n
Bclk il_clk 0 V = lvc(V(v18), V(il_clk_rc) > 0.95)
* U909 74LVC1G74: D = GATES_PINCHED, CLK = IL_CLK, ~CLR = IL_CLR_N, Q = PA_ARMED (XSPICE d_dff).
* nominal: VCC < lvc_vmin clears; pessimistic: VCC < lvc_vmin SETS (undefined state = armed)
Brst rst_a 0 V = (V(il_clr_n) < {kth}*V(v18) && !({pess} > 0.5 && V(v18) < {lvc_vmin})) || ({pess} < 0.5 && V(v18) < {lvc_vmin}) ? 1.8 : 0
Bset set_a 0 V = ({pess} > 0.5 && V(v18) < {lvc_vmin} && V(il_clr_n) > 0.35*V(v18)) ? 1.8 : 0
Bdin d_a 0 V = V(gates_pinched) > {kth}*V(v18) ? 1.8 : 0
abr1 [il_clk d_a rst_a set_a] [clk_d d_d rst_d set_d] adcb
.model adcb adc_bridge(in_low=0.7 in_high=0.9)
aff d_d clk_d set_d rst_d q_d qb_d ff74
.model ff74 d_dff(clk_delay=13.4e-9 set_delay=14.4e-9 reset_delay=14.4e-9)
abr2 [q_d] [pa_armed_l] dacb
.model dacb dac_bridge(out_low=0 out_high=1 t_rise=1n t_fall=1n)
Barm pa_armed 0 V = V(pa_armed_l) * V(v18)
* U705 74LVC1G11: PA_DRAIN_EN = PA_ARMED . WDT_OK . NEG_OK ; 1k series ; R965 100k pull-down ; supervisor clamp
Band pa_drain_en_s 0 V = lvc(V(v18), V(pa_armed) > {kth}*V(v18) && V(wdt_ok) > {kth}*V(v18) && V(neg_ok) > {kth}*V(v18))
Rand pa_drain_en_s pa_drain_en 1k
R965 pa_drain_en 0 100k
Dand   pa_drain_en dk2 dbat54
Rand_d dk2 pg_3v3rf {1e12-sup_en*(1-fetclamp)*(1e12-0.5)}
* fetclamp=1 (candidate M5 fix): BAT54C replaced by two DMG1012T clamps (drain on PA_DRAIN_EN / IL_CLR_N, source GND)
* whose gates share IL_Q3G with Q3, so PG_3V3RF carries no clamp current
Bfc1 pa_drain_en 0 I = {fetclamp}*clip01((V(il_q3g)-{q2_vth})/0.3)*V(pa_drain_en)/0.7
Bfc2 il_clr_n 0 I = {fetclamp}*clip01((V(il_q3g)-{q2_vth})/0.3)*V(il_clr_n)/0.7

* --- chain 1 TPS22810 drain switch (CT 2200 pF). EN rising 1.23 / falling 1.13 V typ -> 1.18 V nominal,
*     1.08 V (VENF min) pessimistic. tOFF 3.3 us. At VIN 5 V: tD ~134 us, tR ~186 us -> 5 V/232 us.
*     Ron 79 mohm. QOD RPD (250..400 ohm) when off, needs VIN > 2.7 V (assumed) ---
Bsw_en  sw_en 0 V = V(pa_drain_en) > ({pess} > 0.5 ? 1.08 : 1.18) ? 1 : 0
Tsw     sw_en 0 sw_en_d 0 Z0=50 TD={tsw_off}
Rsw_t   sw_en_d 0 50
Btm_sw  0 tm_sw I = V(sw_en_d) > 0.5 ? 1m : -V(tm_sw)
Ctm_sw  tm_sw 0 1u
Vsns    v5pa sw_in 0
Bsw     sw_in vout I = V(sw_en_d) > 0.5 ? max(0, min(V(sw_in), 21.55*max(0, V(tm_sw)-0.1307)) - V(vout))/0.079 : 0
Bqod    vout 0 I = (V(sw_en_d) < 0.5 && V(sw_in) > 2.7) ? V(vout)/{rpd} : 0
* other three chains on +5V_PA: mirror of chain 1 (ASSUMPTION)
Bmirror v5pa 0 I = 3*I(Vsns)
* drain decoupling per chain: 4 x 4.7 uF (VDD_PA, ADI Stingray) + 1 uF + 10 nF + 100 pF (amendment A5)
Cvout vout 0 {cvout}
* --- 4 x ADTR1107 PA drain current: idss(Vg) * tanh(Vds / 0.5 V) (knee 0.5 V ASSUMPTION) ---
Bi1 ipa1 0 V = idss(V(gate1)) * tanh(max(V(vout),0)/0.5)
Bi2 ipa2 0 V = idss(V(gate2)) * tanh(max(V(vout),0)/0.5)
Bi3 ipa3 0 V = idss(V(gate3)) * tanh(max(V(vout),0)/0.5)
Bi4 ipa4 0 V = idss(V(gate4)) * tanh(max(V(vout),0)/0.5)
Bpa vout 0 I = V(ipa1) + V(ipa2) + V(ipa3) + V(ipa4)

* --- drain crowbar candidate (cb_en), per chain on +5V_PA_C1 (= VOUT):
*     Q2 (small N-MOSFET, Vth q2_vth) gate = PA_DRAIN_EN through q2_r / q2_c; Q2 on -> crowbar gate held low (2 ohm).
*     Crowbar gate pulled up from +5V_PA (switch input) by cb_rpu, Ciss 1 nF. Crowbar conductance rises linearly
*     from cb_vth to 4.5 V VGS; total on-resistance cb_r (Rds(on) + series pulse resistor) ---
Rq2   pa_drain_en q2g {q2_r}
Cq2   q2g 0 {q2_c}
Bcbpu v5pa cbg I = {cb_en}*(V(v5pa)-V(cbg))/{cb_rpu}
Bq2   cbg 0 I = clip01((V(q2g)-{q2_vth})/0.3)*V(cbg)/0.7
* other three chains' Q2 RC branches load PA_DRAIN_EN (3 x 10k / 1 nF, as built)
Rq2x  pa_drain_en q2gx {q2_r/3}
Cq2x  q2gx 0 {3*q2_c}
Ccbg  cbg 0 {cb_ciss}
Rlk1  cbg 0 1G
Rlk2  vout 0 1G
Rlk3  vneg 0 1G
Bicb  icb 0 V = {cb_en} * clip01((V(cbg)-{cb_vth})/(4.5-{cb_vth})) * max(V(vout),0)/{cb_r}
Bcb   vout 0 I = V(icb)

.options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-5 itl4=100
