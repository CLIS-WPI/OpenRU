# Worst-case calc for PA_BIAS -> divider -> VGG_PA. Inputs are datasheet values cited in GATE_BIAS_ANALYSIS.md.
import math
E96=[100,102,105,107,110,113,115,118,121,124,127,130,133,137,140,143,147,150,154,158,162,165,169,174,178,182,187,191,196,200,205,210,215,221,226,232,237,243,249,255,261,267,274,280,287,294,301,309,316,324,332,340,348,357,365,374,383,392,402,412,422,432,442,453,464,475,487,499,511,523,536,549,562,576,590,604,619,634,649,665,681,698,715,732,750,768,787,806,825,845,866,887,909,931,953,976]
LSB=4.8/255
TOL=0.001; TCR=25e-6; DT=65   # 0.1 %, 25 ppm/K, 25->90 C board
def k(r1,r2): return r2/(r1+r2)
def kmax(r1,r2): e=TOL+TCR*DT; return r2*(1+e)/(r1*(1-e)+r2*(1+e))
def kmin(r1,r2): e=TOL+TCR*DT; return r2*(1-e)/(r1*(1+e)+r2*(1-e))
# pick pair: k nominal near 0.370, total ~1 kOhm
best=sorted(((abs(k(a,b)-0.370)+abs(a+b-1000)/1e5,a,b) for a in E96 for b in E96 if 900<=a+b<=1100))[:5]
for _,a,b in best: print('cand R1=%d R2=%d k=%.5f'%(a,b,k(a,b)))
r1,r2=best[0][1],best[0][2]
kn,kx,km=k(r1,r2),kmax(r1,r2),kmin(r1,r2); rth=r1*r2/(r1+r2)
print(f'\nR1={r1} R2={r2} k={kn:.5f} kmax={kx:.5f} kmin={km:.5f} Rth={rth:.1f} ohm Rtot={r1+r2}')
for lbl,v in [('ADAR1000 AVDD1 spec max |-5.25|',5.25),('H2 -5V_BF worst |-5.150| (POWER_SPEC)',5.150),('DAC 0xFF typ -4.8',4.8),('ADAR1000 AVDD1 abs max -5.5',5.5),('LDO pass short -> PWR_VNEG -6.688',6.688)]:
    print(f'  bound {lbl}: VGG = -{kx*v:.3f} V (margin to -2.0: {2.0-kx*v:+.3f} V)')
print('  margin-product limit (2.0/1.75)*(4.8/5.25) =',round(2/1.75*4.8/5.25,4),' with -5.150:',round(2/1.75*4.8/5.150,4))
for vg in (0.25,1.1,1.75,1.80):
    d=vg/km; print(f'  VGG -{vg}: DAC needed (kmin) -{d:.3f} V code {d/LSB:.1f}; (knom) -{vg/kn:.3f} V code {vg/kn/LSB:.1f}')
print(f'  max reach at code 0xFF (-4.8 typ): -{km*4.8:.3f} (kmin) .. -{kx*4.8:.3f} (kmax)')
print(f'  if DAC limited to |AVDD1|min-h, AVDD1=-4.848: h=0.1 -> -{km*4.748:.3f}; h=0.2 -> -{km*4.648:.3f}; h=0.3 -> -{km*4.548:.3f}')
print(f'  LSB at VGG: {kn*LSB*1e3:.2f} mV (direct {LSB*1e3:.2f} mV)')
for v in (1.1/kn,1.75/kn,4.8,5.25): print(f'  DAC load at -{v:.2f} V: {v/(r1+r2)*1e3:.2f} mA (limit 10 mA)')
print(f'  16 PA ch in OFF: {16*1.75/kn/(r1+r2)*1e3:.0f} mA extra on -5V_BF')
for c in (10e-9,1e-9):
    tau=rth*c; print(f'  C={c*1e9:.0f} nF tau={tau*1e6:.3f} us, 1% settle {4.6*tau*1e6:.2f} us, 0.1% {6.9*tau*1e6:.2f} us')
for i in (0.05e-3,0.3e-3,0.5e-3):
    print(f'  IGG {i*1e3:.2f} mA -> dVGG {i*rth*1e3:.0f} mV -> dIDQ ~{i*rth*500:.0f} mA (Fig49 slope ~500 mA/V)')
print(f'  positive excursion +0.7 V at DAC pin -> VGG +{0.7*kx:.2f} V')
# self-checks
assert kx*5.25<2.0 and km<kn<kx and (r1+r2)>4.8/0.010
