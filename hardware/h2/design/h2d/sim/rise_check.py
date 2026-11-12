"""Rising-edge (re-arm) BBM margin for candidate A: time from crowbar gate < 0.3 V to the first instant the
eFuse FET may conduct (SHDN_c > 0.8 V, zero turn-on delay assumed). BEHAVIOURAL / PRELIMINARY."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arch_a_sim as A
res = []
for sn, sc in A.scenarios():
    if not (sn.startswith('S2') or sn.startswith('S4')):
        continue
    for cc in A.corners():
        c = dict(cc); c.update(sc); c['name'] = 'rise_' + sn + '_' + cc['tag']
        t, v = A.run(c)
        os.remove(os.path.join(A.OUT, c['name'] + '.dat'))
        tr = 20e-6                                  # P released at T0 in S2 and S4
        on = np.where((t > tr) & (v['v(fon)'] > 0.5))[0]
        if not len(on):
            continue                                # glitch too short for SHDN to reach 0.8 V
        off = np.where((t > tr) & (t < t[on[0]]) & (v['v(gate)'] < 0.3))[0]
        res.append((sn, cc['tag'], (t[on[0]] - t[off[0]]) * 1e6))
w = min(res, key=lambda r: r[2])
print(f"runs with FET turn-on after release: {len(res)}; min rising BBM margin {w[2]:.2f} us ({w[0]}, {w[1]})")
assert w[2] > 0
