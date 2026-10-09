# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces Section 3.3 ("Numerical order of accuracy") of the manuscript.

Finding that motivated the two-part design below: on the Go-model landscape,
a long-time (T=2) trajectory error against a fine reference solution mixes
true truncation error with "discrete attractor branching" (different dt
values falling into different basins), so apparent convergence order
becomes irregular. The order claimed in the abstract (p = 2.00 +/- 0.02)
is therefore verified on:
  (A) a smooth, single-well, non-commuting test problem (no basins to branch
      into) -- reaches p = 2.00 +/- 0.02 for a=0 over the whole range and for a=4
      for dt <= 2^-8 (coarser steps give p = 3.06, 2.30, 2.08, 2.02), and
  (B) a short time window on the Go-model landscape, both against a fine
      reference solution at dt_ref. (B) still shows irregular, sometimes
      negative apparent order at the coarser end of the dt range tested
      here -- this reproduces, rather than contradicts, the "discrete
      attractor branching" phenomenon documented in
      ../docs/convergence_verification.md: once dt is small enough (roughly
      dt <~ 2**-10 in self-convergence terms, see script 04), the same
      p~2 order is recovered on the Go model too.

See 04_self_convergence_richardson.py for a reference-solution-free
(self-convergence / Richardson) cross-check of the same claim, which shows
this small-dt recovery directly on the Go model.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np

# ---------- (A) smooth, anisotropic, non-commuting test problem ----------
K = np.array([1.0, 50.0])

def U(x):
    return 0.5 * np.sum(K * x * x) + 0.25 * x[0] ** 4 + 0.5 * x[0] ** 2 * x[1] ** 2

def gU(x):
    return K * x + np.array([x[0] ** 3 + x[0] * x[1] ** 2, x[0] ** 2 * x[1]])

def Hs(x):
    return np.diag(K) + np.array([[3 * x[0] ** 2 + x[1] ** 2, 2 * x[0] * x[1]],
                                   [2 * x[0] * x[1], x[0] ** 2]])

gv = np.array([1.0, 0.2])
s_ = np.sqrt(gv)
J = np.array([[0, 1.0], [-1, 0]])

def Amat(a):
    return a * (s_[:, None] * J) * s_[None, :]

def dgrad2(x, y):
    m = 0.5 * (x + y)
    d = y - x
    g = gU(m)
    n2 = d @ d
    return g if n2 < 1e-30 else g + ((U(y) - U(x) - g @ d) / n2) * d

def dg_step2(M, x, dt, tol=1e-13, maxit=50):
    y = x - dt * (M @ gU(x))
    for _ in range(maxit):
        r = y - x + dt * (M @ dgrad2(x, y))
        if np.linalg.norm(r) < tol:
            return y
        y = y - np.linalg.solve(np.eye(2) + 0.5 * dt * M @ Hs(0.5 * (x + y)), r)
    return None

def integrate2(M, x0, T, dt):
    x = x0.copy()
    for _ in range(int(round(T / dt))):
        x = dg_step2(M, x, dt)
        if x is None:
            return None
    return x

def test_smooth(a, T=1.0, dt_ref=2 ** -14):
    M = np.diag(gv) + Amat(a)
    x0 = np.array([1.3, 0.4])
    x_ref = integrate2(M, x0, T, dt_ref)
    print(f"--- (A) smooth single-well problem, a={a}, T={T} ---")
    print(f"{'dt':>10} {'error':>14} {'order p':>10}")
    prev = None
    for k in range(3, 12):
        dt = 2 ** -k
        x = integrate2(M, x0, T, dt)
        e = np.linalg.norm(x - x_ref) if x is not None else np.nan
        p = np.log2(prev / e) if (prev and e and e > 0) else np.nan
        print(f"{dt:>10.6f} {e:>14.6e} {p:>10.3f}")
        prev = e

# ---------- (B) Go-model: local (short-window) order ----------
from mfd_discrete_gradient import GoLandscape, CapMob, CirMob, dg_step, make_native

def integrate_fixed(land, M3, x0, T, dt):
    x, Ux = x0.copy(), land.energy_grad(x0)[0]
    for _ in range(int(round(T / dt))):
        out = dg_step(land, M3, x, Ux, dt)
        if out is None:
            return None
        x, Ux = out
    return x, Ux

def test_gomodel_short(a, T, dt_ref):
    n = 20
    x_nat = make_native(n, 0)
    land, cap, cir = GoLandscape(x_nat), CapMob(n), CirMob(n, a)
    M3 = np.kron(np.diag(cap.g) + cir.matrix(cap.g), np.eye(3))
    rng = np.random.default_rng(0)
    x0 = np.c_[np.arange(n, dtype=float), np.zeros((n, 2))] + 0.05 * rng.normal(size=(n, 3))
    ref = integrate_fixed(land, M3, x0, T, dt_ref)
    x_ref = ref[0]
    print(f"--- (B) Go model, a={a}, T={T} (short window; see module docstring "
          f"re. discrete attractor branching at coarser dt) ---")
    print(f"{'dt':>10} {'error':>14} {'order p':>10}")
    prev = None
    for k in range(4, 11):
        dt = 2 ** -k
        r = integrate_fixed(land, M3, x0, T, dt)
        e = np.linalg.norm(r[0] - x_ref) if r is not None else np.nan
        p = np.log2(prev / e) if (prev and e and e > 0) else np.nan
        print(f"{dt:>10.6f} {e:>14.6e} {p:>10.3f}")
        prev = e

if __name__ == "__main__":
    test_smooth(0.0)
    test_smooth(4.0)
    test_gomodel_short(0.0, T=0.1, dt_ref=2 ** -14)
    test_gomodel_short(4.0, T=0.1, dt_ref=2 ** -14)
