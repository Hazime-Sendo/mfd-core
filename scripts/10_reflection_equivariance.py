# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reflection-equivariance check (supports the label discussion in the manuscript).

R: x -> (-x, y, z) applied to every bead. The Go-model potential depends only on inter-bead
distances, so U(Rx) = U(x) and grad U(Rx) = R grad U(x); the mobilities G and A act on the bead
index (A = a sqrt(G) J sqrt(G) with J coupling neighbouring beads), so they commute with R.
The dynamics is therefore equivariant for every a: the trajectory from R x0 is R x(t).
The mirror structure is x_mir = R x_nat, and the Kabsch RMSD (rotations only) satisfies
rmsd(Ra, Rb) = rmsd(a, b). Consequently the terminal states NATIVE and MIRROR_TRAP must swap, with
identical times, energies and clip times, when the initial chain is reflected.

This script runs seeds 0-9 for a in {0, 4, 16} at D_max=500 (dt=5e-3, max_steps=20000) twice
(original and reflected initial condition) and reports: label swaps, time differences,
max |U| difference and max |x_reflected - R x| at termination.

Run from the repository root:  python3 scripts/10_reflection_equivariance.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from mfd_discrete_gradient import simulate_dg  # noqa: E402

SWAP = {"NATIVE": "MIRROR_TRAP", "MIRROR_TRAP": "NATIVE", "KINETIC_TRAP": "KINETIC_TRAP"}
R = np.array([-1.0, 1.0, 1.0])


def main(a_values=(0.0, 4.0, 16.0), seeds=range(10), d_max=500.0):
    n_total = n_ok = 0
    worst_t = worst_U = worst_x = 0.0
    for a in a_values:
        print(f"a = {a:g}")
        for s in seeds:
            kw = dict(n=20, dt=5e-3, d_max=d_max, a=a, seed=s, native_seed=0, max_steps=20000)
            r0 = simulate_dg(**kw)
            r1 = simulate_dg(reflect_x0=True, **kw)
            expected = SWAP.get(r0["state"], r0["state"])
            ok = (r1["state"] == expected)
            n = min(len(r0["U"]), len(r1["U"]))
            dU = float(np.max(np.abs(r0["U"][:n] - r1["U"][:n])))
            dt_ = abs(r0["t_phys"] - r1["t_phys"])
            dx = float(np.max(np.abs(r1["x"] - r0["x"] * R))) if ok else float('nan')
            worst_t, worst_U = max(worst_t, dt_), max(worst_U, dU)
            if ok:
                worst_x = max(worst_x, dx)
            n_total += 1
            n_ok += int(ok and dt_ == 0.0)
            print(f"  seed {s}: {r0['state']:>12} -> reflected {r1['state']:>12} "
                  f"(expected {expected:>12}) {'OK ' if ok else 'MISMATCH'} "
                  f"|dt|={dt_:.3g} max|dU|={dU:.3g} max|dx|={dx:.3g}")
    print(f"\nlabel swap and identical time in {n_ok}/{n_total} runs; "
          f"worst |dt|={worst_t:.3g}, worst max|dU|={worst_U:.3g}, worst max|dx|={worst_x:.3g}")
    return n_ok == n_total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
