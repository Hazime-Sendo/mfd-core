# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Structure-preserving integrator: Gonzalez discrete-gradient step for xdot = -(G + A) grad U,
solved implicitly for the symmetric and antisymmetric parts together:

    y = x - h*s*(G + A) gradbar U(x, y),
    gradbar U(x,y) = grad U(m) + [(U(y) - U(x) - grad U(m).d)/|d|^2] d,  m = (x+y)/2, d = y - x

so that U(y) - U(x) = -h*s * gradbar U . G gradbar U <= 0 (the A term cancels by antisymmetry).
Newton failure triggers step halving. s is the DiBaS time-rescaling factor.
`run_go_fold` is the batch-trial interface used by the sweep scripts.
"""
import numpy as np
from metriplectic_folding import (GoLandscape, CapMob, CirMob, FoldDiag,
                                  make_native, kabsch_rmsd)

I3 = np.eye(3)

def _pair_hess(x, i, j, r0, k, H):
    r = x[i] - x[j]; d = np.linalg.norm(r, axis=1); rh = r / d[:, None]
    B = 2 * k * ((1 - r0 / d)[:, None, None] * I3
                 + (r0 / d)[:, None, None] * rh[:, :, None] * rh[:, None, :])
    a3 = np.arange(3)
    for p, q, sgn in [(i, i, 1), (j, j, 1), (i, j, -1), (j, i, -1)]:
        rows = 3 * p[:, None, None] + a3[None, :, None]
        cols = 3 * q[:, None, None] + a3[None, None, :]
        np.add.at(H, (np.broadcast_to(rows, B.shape), np.broadcast_to(cols, B.shape)), sgn * B)

def hessian(land, x):
    H = np.zeros((3 * land.n, 3 * land.n))
    _pair_hess(x, land.bi, land.bj, land.b0, land.k, H)
    _pair_hess(x, land.ci, land.cj, land.c0, land.eps, H)
    return H

def dgrad(land, x, y, Ux, Uy):
    m = 0.5 * (x + y); d = y - x
    g = land.energy_grad(m)[1]; n2 = np.sum(d * d)
    return g if n2 < 1e-30 else g + ((Uy - Ux - np.sum(g * d)) / n2) * d

def dg_try(land, M3, x, Ux, h, tol=1e-10, maxit=30):
    n3 = x.size
    y = x - h * (M3 @ land.energy_grad(x)[1].ravel()).reshape(x.shape)
    for _ in range(maxit):
        Uy = land.energy_grad(y)[0]
        r = (y - x).ravel() + h * (M3 @ dgrad(land, x, y, Ux, Uy).ravel())
        if not np.all(np.isfinite(r)): return None
        if np.linalg.norm(r) < tol * (1 + np.linalg.norm(x)): return y, Uy
        Jm = np.eye(n3) + 0.5 * h * M3 @ hessian(land, 0.5 * (x + y))
        y = y - np.linalg.solve(Jm, r).reshape(x.shape)
    return None

def dg_step(land, M3, x, Ux, h, depth=0):
    out = dg_try(land, M3, x, Ux, h)
    if out is not None or depth > 10: return out
    mid = dg_step(land, M3, x, Ux, h / 2, depth + 1)
    return None if mid is None else dg_step(land, M3, mid[0], mid[1], h / 2, depth + 1)

def simulate_dg(n=20, T_phys=60.0, dt=5e-3, d_max=500.0, a=0.0, seed=0,
                native_seed=0, every=20, max_steps=None, reflect_x0=False, **diag_kwargs):
    x_nat = make_native(n, native_seed)
    rng = np.random.default_rng(seed)
    x = np.c_[np.arange(n, dtype=float), np.zeros((n, 2))] + 0.1 * rng.normal(size=(n, 3))
    if reflect_x0:                       # test hook: reflect the initial chain, x -> (-x, y, z)
        x = x * np.array([-1.0, 1.0, 1.0])
    land, cap, cir = GoLandscape(x_nat), CapMob(n), CirMob(n, a)
    diag = FoldDiag(land, x_nat, window=max(10, int(1.0 / dt)), hold=diag_kwargs.pop('hold', 5), **diag_kwargs)
    Ux, grad = land.energy_grad(x)
    U_hist, rate_ratio, clip_time = [Ux], [], 0.0
    n_steps = max_steps if max_steps is not None else int(T_phys / dt)
    for t in range(n_steps):
        M = np.diag(cap.g) + cir.matrix(cap.g)
        M3 = np.kron(M, I3)
        D = float(np.sum(grad * (cap.g[:, None] * grad)))
        s = min(1.0, d_max / D) if D > 0 else 1.0          # DiBaS：時間スケーリング
        for _ in range(4):
            out = dg_step(land, M3, x, Ux, dt * s)
            rate = (Ux - out[1]) / dt
            if rate <= d_max * 1.001: break
            s *= d_max / rate
        x, Ux = out; grad = land.energy_grad(x)[1]
        cap.relax(land.local_Q(x), dt)
        U_hist.append(Ux); rate_ratio.append(rate / d_max)
        diag.record(Ux, s < 0.999)
        clip_time += dt * (s < 0.999)
        if t % every == 0 and diag.evaluate(x) in FoldDiag.TERMINAL:
            break
    return dict(state=diag.state, t_phys=(t + 1) * dt, U=np.array(U_hist), clip_time=clip_time,
                max_rate_ratio=max(rate_ratio), x=x, x_nat=x_nat)


_LABEL = {"NATIVE": "natural", "MIRROR_TRAP": "mirror", "KINETIC_TRAP": "local"}

def run_go_fold(a, D_max, dt, max_steps, trials, n=20, native_seed=0, return_runs=False):
    """sweep_D_max 用のインターフェース。times は終端状態に到達した試行のみ（打ち切りは unfinished）"""
    stats = dict(natural=0, mirror=0, local=0, unfinished=0, times=[], dU_max=-np.inf)
    runs = []
    for s in range(trials):
        r = simulate_dg(n=n, dt=dt, d_max=D_max, a=a, seed=s,
                        native_seed=native_seed, max_steps=max_steps)
        key = _LABEL.get(r["state"], "unfinished")
        stats[key] += 1
        if key != "unfinished":
            stats["times"].append(r["t_phys"])
        stats["dU_max"] = max(stats["dU_max"], float(np.diff(r["U"]).max()))
        runs.append(dict(seed=s, state=r["state"], t=r["t_phys"], U0=float(r["U"][0]),
                         clip_time=r["clip_time"]))
    return (stats, runs) if return_runs else stats
