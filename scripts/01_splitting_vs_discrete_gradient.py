# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces Figure 2 of the manuscript (Section 5.1 / Remark 1):
monotonicity region, in the (a, h) plane, of a naive operator-split
integrator versus the unified Gonzalez discrete-gradient step, on an
explicit non-commuting test potential

    U(x) = 0.5*(x1^2 + 50*x2^2) + 0.25*x1^4 + 0.5*x1^2*x2^2

with symmetric mobility G = diag(1.0, 0.2) and antisymmetric mobility
A = a * sqrt(G) J sqrt(G).

Writes fig2_data.json (a_list, dt_list and four {0,1} grids; 1 = monotone over 400 steps):
  split            naive operator splitting
  dg               unified step, plain Newton solve, NO step bisection (0 = Newton failed or U increased)
  dg_bisect        unified step with the recursive step bisection described in Section 3.1
  dg_u_increased   1 = the plain-Newton unified step produced an increase of U (never happens)
  split_u_increased 1 = splitting produced an increase of U (0 with split=0 means non-finite)
Note: the failures of "dg" are all Newton non-convergence in the first step; U never increases.
The plain-Newton comparison therefore measures the convergence range of the nonlinear solve,
not a loss of the monotonicity identity.
"""
import numpy as np
import json
import os

K = np.array([1.0, 50.0])

def U(x):
    return 0.5 * np.sum(K * x * x) + 0.25 * x[0] ** 4 + 0.5 * x[0] ** 2 * x[1] ** 2

def gU(x):
    return K * x + np.array([x[0] ** 3 + x[0] * x[1] ** 2, x[0] ** 2 * x[1]])

def H(x):
    return np.diag(K) + np.array([[3 * x[0] ** 2 + x[1] ** 2, 2 * x[0] * x[1]],
                                   [2 * x[0] * x[1], x[0] ** 2]])

gv = np.array([1.0, 0.2])
s = np.sqrt(gv)
J = np.array([[0, 1.0], [-1, 0]])

def Amat(a):
    return a * (s[:, None] * J) * s[None, :]

def user_step(x, G, A, dt):
    """Naive operator splitting: dissipative sub-step, then circulatory sub-step
    (implicit midpoint on the circulatory part alone)."""
    xd = x - dt * (G @ gU(x))
    xn = xd.copy()
    for _ in range(5):
        xn = xd - dt * (A @ gU(0.5 * (xd + xn)))
    return xn

def dgrad(x, y):
    m = 0.5 * (x + y)
    d = y - x
    g = gU(m)
    n2 = d @ d
    return g if n2 < 1e-30 else g + ((U(y) - U(x) - g @ d) / n2) * d

def dg_step(x, A, dt, tol=1e-13, maxit=50):
    """Unified Gonzalez discrete-gradient step for the full (G+A) vector field."""
    M = np.diag(gv) + A
    y = x - dt * (M @ gU(x))
    for _ in range(maxit):
        r = y - x + dt * (M @ dgrad(x, y))
        if not np.all(np.isfinite(r)):
            return None
        if np.linalg.norm(r) < tol:
            return y
        y = y - np.linalg.solve(np.eye(2) + 0.5 * dt * M @ H(0.5 * (x + y)), r)
    return None

a_list = [0, 1, 2, 3, 4, 6, 8, 10, 12, 16, 24, 32, 48, 64]
dt_list = [0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001]

def dg_step_bisect(x, A, dt, depth=0):
    """Unified step with recursive step bisection if Newton fails (Section 3.1)."""
    y = dg_step(x, A, dt)
    if y is not None:
        return y
    if depth > 20:
        return None
    m = dg_step_bisect(x, A, dt / 2, depth + 1)
    return None if m is None else dg_step_bisect(m, A, dt / 2, depth + 1)

def grid(stepfun, kind, return_increase=False):
    out = np.zeros((len(a_list), len(dt_list)))
    inc = np.zeros((len(a_list), len(dt_list)))
    for i, a in enumerate(a_list):
        for j, dt in enumerate(dt_list):
            A = Amat(a)
            x = np.array([1.5, 0.3])
            Up = U(x)
            ok = True
            for _ in range(400):
                if kind == 'split':
                    x = stepfun(x, np.diag(gv), A, dt)
                    if not np.all(np.isfinite(x)):
                        ok = False
                        break
                    Un = U(x)
                else:
                    y = stepfun(x, A, dt)
                    if y is None:
                        ok = False
                        break
                    x = y
                    Un = U(x)
                if Un > Up + 1e-10:
                    ok = False
                    inc[i, j] = 1.0
                    break
                Up = Un
            out[i, j] = 1.0 if ok else 0.0
    return (out, inc) if return_increase else out

if __name__ == "__main__":
    split_grid, split_inc = grid(user_step, 'split', True)
    dg_grid, dg_inc = grid(dg_step, 'dg', True)
    bis_grid = grid(dg_step_bisect, 'dg')
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'fig2_data.json')
    with open(out_path, 'w') as f:
        json.dump(dict(a_list=a_list, dt_list=dt_list,
                       split=split_grid.tolist(), dg=dg_grid.tolist(),
                       dg_bisect=bis_grid.tolist(),
                       dg_u_increased=dg_inc.tolist(),
                       split_u_increased=split_inc.tolist()), f)
    print("split (naive operator splitting) stable cells:", int(split_grid.sum()), "/", split_grid.size)
    print("dg (unified discrete-gradient) stable cells:  ", int(dg_grid.sum()), "/", dg_grid.size)
    print("dg with step bisection monotone cells:          ", int(bis_grid.sum()), "/", bis_grid.size)
    print("cells where the plain-Newton unified step increased U:", int(dg_inc.sum()))
    print("cells where splitting increased U:", int(split_inc.sum()), "(non-finite otherwise)")
    print(f"wrote {out_path}")
