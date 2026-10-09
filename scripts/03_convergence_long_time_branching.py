# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces the FIRST (superseded) convergence check, kept here because the
manuscript explicitly reports its outcome (Section 3.3): a long-time (T=2)
Go-model trajectory error against a fine reference solution does not show
clean second-order convergence, because different dt values fall into
different basins of attraction ("discrete attractor branching") -- a
genuine, reportable phenomenon, not an integrator bug. See
02_convergence_smooth_and_gomodel.py and 04_self_convergence_richardson.py
for the controls that isolate and confirm the true p=2 truncation-error
order.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from mfd_discrete_gradient import GoLandscape, CapMob, CirMob, dg_step, make_native

def integrate_fixed(land, cap, cir, x0, T, dt):
    x, Ux = x0.copy(), land.energy_grad(x0)[0]
    M3 = np.kron(np.diag(cap.g) + cir.matrix(cap.g), np.eye(3))
    n_steps = int(round(T / dt))
    for _ in range(n_steps):
        out = dg_step(land, M3, x, Ux, dt)
        if out is None:
            return None
        x, Ux = out
    return x, Ux

def run(a, T=2.0, n=20, native_seed=0, x0_seed=0, dt_ref=2 ** -13):
    x_nat = make_native(n, native_seed)
    land, cap, cir = GoLandscape(x_nat), CapMob(n), CirMob(n, a)
    rng = np.random.default_rng(x0_seed)
    x0 = np.c_[np.arange(n, dtype=float), np.zeros((n, 2))] + 0.05 * rng.normal(size=(n, 3))

    ref = integrate_fixed(land, cap, cir, x0, T, dt_ref)
    assert ref is not None, "reference failed"
    x_ref = ref[0]

    dts = [2 ** -k for k in range(3, 11)]
    errs = []
    for dt in dts:
        r = integrate_fixed(land, cap, cir, x0, T, dt)
        errs.append(np.linalg.norm(r[0] - x_ref) if r is not None else np.nan)
    return dts, errs

if __name__ == "__main__":
    for a in [0.0, 4.0]:
        dts, errs = run(a)
        print(f"=== a={a}, T=2.0 (long-time, multi-basin) ===")
        print(f"{'dt':>10} {'error':>14} {'order p':>10}")
        prev = None
        for dt, e in zip(dts, errs):
            p = np.log2(prev / e) if (prev and e and prev > 0 and e > 0) else float('nan')
            print(f"{dt:>10.5f} {e:>14.6e} {p:>10.3f}")
            prev = e
