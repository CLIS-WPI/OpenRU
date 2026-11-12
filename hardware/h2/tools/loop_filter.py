#!/usr/bin/env python3
"""ADF4371 3rd-order passive loop filter for f_PFD = 10 MHz, LO = 6.6 GHz (integer N = 660).

DERIVED, not ADI-verified: ADF4371 Rev 0 gives no reference filter and says to use ADIsimPLL. Inputs taken
from the datasheet: Kv nominal 50 MHz/V ("provides the most accurate KV", p23), Icp 1.75 mA (REG001E default 0x4),
N divider driven from the VCO (6.6 GHz is inside the 4-8 GHz fundamental range). Classic 2nd-order design
(T1/T2 for a phase margin), plus an R3/C3 pole for reference-spur attenuation, then a numeric check of the
actual crossover and phase margin with the chosen standard values.
"""
import cmath
import math

KV, ICP, N, FPFD = 50e6, 1.75e-3, 660, 10e6
FC, PM = 100e3, 50.0

wc = 2 * math.pi * FC
phi = math.radians(PM)
T1 = (1 / math.cos(phi) - math.tan(phi)) / wc
T2 = 1 / (wc ** 2 * T1)
C1 = ICP * KV / (wc ** 2 * N) * T1 / T2 * math.sqrt((1 + (wc * T2) ** 2) / (1 + (wc * T1) ** 2))
C2 = C1 * (T2 / T1 - 1)
R2 = T2 / C2
print(f"ideal: C1={C1 * 1e12:.0f} pF  C2={C2 * 1e12:.0f} pF  R2={R2:.0f} ohm")

# chosen standard values (E12/E24) + 3rd pole ~3.3 MHz (3x below f_PFD; keeps PM > 45 deg)
c1, c2, r2, r3, c3 = 120e-12, 820e-12, 5.6e3, 2.2e3, 22e-12


def zf(s):
    """Impedance seen by the charge pump times the R3/C3 transfer to VTUNE."""
    z2 = r2 + 1 / (s * c2)
    zc3 = 1 / (s * c3)
    zbranch3 = r3 + zc3
    zin = 1 / (s * c1 + 1 / z2 + 1 / zbranch3)
    return zin * zc3 / zbranch3


def gol(f):
    s = 2j * math.pi * f
    return ICP * KV * zf(s) / (s * N)  # Kphi*Kvco = (Icp/2pi)*(2pi*Kv) = Icp*Kv


lo, hi = 1e3, 5e6
for _ in range(200):  # bisection on |G| = 1
    mid = math.sqrt(lo * hi)
    lo, hi = (mid, hi) if abs(gol(mid)) > 1 else (lo, mid)
fc = math.sqrt(lo * hi)
pm = 180 + math.degrees(cmath.phase(gol(fc)))
att = 20 * math.log10(abs(gol(FPFD)) / abs(gol(fc)))
print(f"chosen: C1=120p C2=820p R2=5.6k R3=2.2k C3=22p -> crossover {fc / 1e3:.1f} kHz, phase margin {pm:.1f} deg, "
      f"open-loop gain at f_PFD {20 * math.log10(abs(gol(FPFD))):.1f} dB, 3rd pole {1 / (2 * math.pi * r3 * c3) / 1e6:.2f} MHz")
assert 60e3 < fc < 150e3 and 45 < pm < 60, "loop filter check failed"
