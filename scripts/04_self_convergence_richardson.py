# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reference-solution-free cross-check of the p=2.00 +/- 0.02 order claim
(Section 3.3 / abstract), by self-convergence: step dt geometrically by
factors of 2 and look at the Cauchy sequence ||x(dt_k) - x(dt_k/2)|| -- if
this ratio tends to 2^p, the scheme is order p, with no external reference
solution required (Richardson self-convergence).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from mfd_discrete_gradient import GoLandscape, CapMob, CirMob, dg_step, make_native

def integrate_fixed(land, M3, x0, T, dt):
    x, Ux = x0.copy(), land.energy_grad(x0)[0]
    n_steps = int(round(T / dt))
    for _ in range(n_steps):
        out = dg_step(land, M3, x, Ux, dt)
        if out is None:
            return None
        x, Ux = out
    return x, Ux

def self_convergence(land, M3, x0, T, k_range):
    xs = {}
    for k in k_range:
        dt = 2.0 ** -k
        r = integrate_fixed(land, M3, x0, T, dt)
        xs[k] = r[0] if r is not None else None
    print(f"{'dt_k':>10} {'diff=|x(dt_k)-x(dt_k/2)|':>26} {'ratio':>8} {'order p':>10}")
    diffs = {}
    for k in k_range[:-1]:
        if xs[k] is None or xs[k + 1] is None:
            diffs[k] = np.nan
            continue
        diffs[k] = np.linalg.norm(xs[k] - xs[k + 1])
    prev = None
    for k in k_range[:-1]:
        dt = 2.0 ** -k
        d = diffs[k]
        ratio = prev / d if (prev and d and d > 0) else np.nan
        p = np.log2(ratio) if ratio == ratio and ratio > 0 else np.nan
        print(f"{dt:>10.6f} {d:>26.6e} {ratio:>8.3f} {p:>10.3f}")
        prev = d

if __name__ == "__main__":
    n = 20
    x_nat = make_native(n, 0)
    rng = np.random.default_rng(1)
    for a in [0.0, 4.0, 16.0]:
        land, cap, cir = GoLandscape(x_nat), CapMob(n), CirMob(n, a)
        M3 = np.kron(np.diag(cap.g) + cir.matrix(cap.g), np.eye(3))
        x0 = x_nat + 0.05 * rng.normal(size=(n, 3))  # near equilibrium: smooth, single-basin region
        print(f"=== Go model, a={a}, T=1.0, x0 near equilibrium ===")
        self_convergence(land, M3, x0, T=1.0, k_range=list(range(3, 13)))
        print()
