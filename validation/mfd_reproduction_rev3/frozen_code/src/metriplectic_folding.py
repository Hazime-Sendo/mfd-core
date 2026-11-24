# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Metriplectic folding dynamics (MFD): model components.

Layer A (physics):  GoLandscape (Go-model potential U), CapMob (self-evolving symmetric
mobility G = diag(g) > 0), CirMob (antisymmetric mobility A = a sqrt(G) J sqrt(G)),
DiBaS (dissipation-rate cap D_max).
Layer B (diagnosis): FoldDiag (terminal-state classifier; reads the dynamics, no feedback).

Continuous model:   dx = -(G + A) grad U dt  [+ sqrt(2 T G) dW for T > 0]
                    dg/dt = -(g - g_eq(Q_loc)) / tau
The explicit integrator `step`/`simulate` here is used only for the stochastic circulation pilot
(scripts/08_circulation_pilot.py); all deterministic results use src/mfd_discrete_gradient.py.
(Original Japanese notes: 蛋白質構造解析工学 ラフスケッチ v3.)
"""
import numpy as np
from collections import deque, Counter

# ======================= A層：物理 =======================
def _pair(x, i, j, r0, k, grad):
    r = x[i] - x[j]
    d = np.linalg.norm(r, axis=1)
    f = (2 * k * (d - r0) / np.maximum(d, 1e-12))[:, None] * r
    np.add.at(grad, i, f); np.add.at(grad, j, -f)
    return k * np.sum((d - r0) ** 2)

class GoLandscape:
    def __init__(self, x_nat, k_bond=100.0, eps=1.0, rc=3.0):
        self.n = n = len(x_nat)
        self.bi, self.bj = np.arange(n - 1), np.arange(1, n)
        self.b0 = np.linalg.norm(x_nat[1:] - x_nat[:-1], axis=1)
        i, j = np.triu_indices(n, k=3)
        d = np.linalg.norm(x_nat[i] - x_nat[j], axis=1)
        m = d < rc
        self.ci, self.cj, self.c0 = i[m], j[m], d[m]
        self.k, self.eps = k_bond, eps
        self.den = (np.bincount(self.ci, minlength=n)
                    + np.bincount(self.cj, minlength=n)).astype(float)

    def energy_grad(self, x):
        grad = np.zeros_like(x)
        U = _pair(x, self.bi, self.bj, self.b0, self.k, grad)
        U += _pair(x, self.ci, self.cj, self.c0, self.eps, grad)
        return U, grad

    def formed(self, x):
        d = np.linalg.norm(x[self.ci] - x[self.cj], axis=1)
        return d < 1.2 * self.c0

    def Q(self, x):
        f = self.formed(x)
        return float(f.mean()) if len(f) else 1.0

    def local_Q(self, x):
        f = self.formed(x).astype(float)
        num = (np.bincount(self.ci, f, self.n) + np.bincount(self.cj, f, self.n))
        return np.divide(num, self.den, out=np.zeros(self.n), where=self.den > 0)

class CapMob:
    """対称移動度 g_i：変異で基準値が変わり、接触形成で局所硬化（自己発展）"""
    def __init__(self, n, g0=1.0, tau=5.0, h=0.3):
        self.g_base = np.full(n, g0)
        self.g = self.g_base.copy()
        self.tau, self.h = tau, h
    def apply_mutation(self, idx, factor):
        self.g_base[idx] *= factor; self.g[idx] *= factor
    def relax(self, Q_loc, dt):
        g_eq = self.g_base * (1 - (1 - self.h) * Q_loc)
        self.g += (g_eq - self.g) * dt / self.tau      # 凸結合なので g>0 を保持

class CirMob:
    """反対称移動度 A = a √G J √G（鎖の N→C 方向性を持つ回転結合）"""
    def __init__(self, n, a):
        J = np.zeros((n, n))
        idx = np.arange(n - 1)
        J[idx, idx + 1], J[idx + 1, idx] = 1.0, -1.0
        self.J, self.a = J, a
    def matrix(self, g):
        s = np.sqrt(g)
        return self.a * (s[:, None] * self.J) * s[None, :]

class DiBaS:
    """エネルギー放出率 D = -∇U·v に上限 D_max（射影係数 D_max/D）"""
    def __init__(self, d_max):
        self.d_max = d_max
    def project(self, v, grad):
        D = float(np.sum(-v * grad))
        if D > self.d_max:
            return v * (self.d_max / D), self.d_max, True
        return v, D, False

# ======================= B層：診断 =======================
def kabsch_rmsd(a, b):
    A, B = a - a.mean(0), b - b.mean(0)
    U, _, Vt = np.linalg.svd(A.T @ B)
    s = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, s]) @ U.T
    return float(np.sqrt(np.mean(np.sum((A @ R.T - B) ** 2, axis=1))))

class FoldDiag:
    """Read-only terminal-state classifier (labels kept for compatibility with data/figures).

    Label semantics: MIRROR_TRAP is NOT an energetic trap; the mirror structure is a minimum of
    the same energy as the native one (reflection symmetry of the Go potential), and the label
    records only which basin (by RMSD) the trajectory ended in. KINETIC_TRAP is a plateau
    label for states away from native and mirror; the plateau test uses a moving window on U
    (no gradient norm), so it can include states stalled near saddle points and is
    threshold-dependent (borderline misclassification is possible).
    """
    TERMINAL = {"NATIVE", "MIRROR_TRAP", "KINETIC_TRAP"}
    def __init__(self, land, x_nat, window=1000, hold=5, eps_U=1e-4,
                 sat_frac=0.8, q_fold=0.9, rmsd_fold=0.5, noise_k=0.3):
        self.land, self.x_nat = land, x_nat
        self.x_mir = x_nat * np.array([-1.0, 1.0, 1.0])
        self.U_buf, self.clip_buf = deque(maxlen=window), deque(maxlen=window)
        self.hold, self.eps_U, self.sat_frac = hold, eps_U, sat_frac
        self.q_fold, self.rmsd_fold, self.noise_k = q_fold, rmsd_fold, noise_k
        self.state, self._cand, self._count = "TRANSIENT", None, 0

    def record(self, U, hit):
        self.U_buf.append(U); self.clip_buf.append(hit)

    def evaluate(self, x):
        if len(self.U_buf) < self.U_buf.maxlen:
            return self.state
        u = np.fromiter(self.U_buf, float); h = len(u) // 2
        plateau = abs(u[h:].mean() - u[:h].mean()) < max(self.eps_U, self.noise_k * u.std())
        if np.mean(self.clip_buf) >= self.sat_frac:
            cand = "OVERLOAD"
        elif plateau:
            q = self.land.Q(x)
            if q >= self.q_fold and kabsch_rmsd(x, self.x_nat) <= self.rmsd_fold:
                cand = "NATIVE"
            elif kabsch_rmsd(x, self.x_mir) <= self.rmsd_fold:
                cand = "MIRROR_TRAP"
            else:
                cand = "KINETIC_TRAP"
        else:
            cand = "FOLDING"
        self._count = self._count + 1 if cand == self._cand else 1
        self._cand = cand
        if self._count >= self.hold:
            self.state = cand
        return self.state

# ======================= 統合 =======================
def make_native(n, native_seed):
    rng = np.random.default_rng(native_seed)
    sv = rng.normal(size=(n - 1, 3))
    sv /= np.linalg.norm(sv, axis=1, keepdims=True)
    return np.vstack([np.zeros(3), np.cumsum(sv, axis=0)])

def step(x, land, cap, cir, dib, T, dt, rng):
    U, grad = land.energy_grad(x)
    v = -cap.g[:, None] * grad - cir.matrix(cap.g) @ grad
    v, D, hit = dib.project(v, grad)
    noise = np.sqrt(2 * T * cap.g * dt)[:, None] * rng.normal(size=x.shape) if T > 0 else 0.0
    x = x + v * dt + noise
    cap.relax(land.local_Q(x), dt)
    return x, U, D, hit, v, grad

def simulate(n=20, steps=30000, dt=1e-3, d_max=500.0, a=0.0, T=0.0,
             mutations=(), native_seed=0, seed=0, every=100, trace=False):
    x_nat = make_native(n, native_seed)
    rng = np.random.default_rng(seed)
    x = np.c_[np.arange(n, dtype=float), np.zeros((n, 2))] + 0.1 * rng.normal(size=(n, 3))
    land, cap, cir, dib = GoLandscape(x_nat), CapMob(n), CirMob(n, a), DiBaS(d_max)
    for idx, fac in mutations:
        cap.apply_mutation(idx, fac)
    diag = FoldDiag(land, x_nat)
    U_hist, D_hist, dyn = [], [], []
    for t in range(steps):
        x, U, D, hit, v, grad = step(x, land, cap, cir, dib, T, dt, rng)
        diag.record(U, hit)
        if trace:
            U_hist.append(U); D_hist.append(D)
            vs = cap.g[:, None] * grad                     # 射影前の対称成分
            vr = cir.matrix(cap.g) @ grad                  # 射影前の反対称成分
            dyn.append(np.linalg.norm(vr) / max(np.linalg.norm(vs), 1e-12))
        if t % every == 0:
            s = diag.evaluate(x)
            if s == "NATIVE" or (T == 0 and s in FoldDiag.TERMINAL):
                break
    return dict(x=x, state=diag.state, t=t, U=np.array(U_hist), D=np.array(D_hist),
                dyn=np.array(dyn), g=cap.g.copy())

def measure_circulation(n=20, steps=40000, dt=1e-3, a=0.0, T=0.05, seed=0, native_seed=0):
    """天然構造近傍の定常状態で、内部座標 q_k=|x_k - x_{k+2}| 平面の符号付き面積速度を測る"""
    x_nat = make_native(n, native_seed)
    rng = np.random.default_rng(seed)
    land, cap, cir, dib = GoLandscape(x_nat), CapMob(n), CirMob(n, a), DiBaS(1e9)
    x = x_nat.copy()
    for _ in range(5000):                      # 緩和（g の硬化も平衡化）
        x = step(x, land, cap, cir, dib, T, dt, rng)[0]
    q = lambda x: np.linalg.norm(x[:-2] - x[2:], axis=1)
    q_old, area = q(x), 0.0
    for _ in range(steps):
        x = step(x, land, cap, cir, dib, T, dt, rng)[0]
        q_new = q(x)
        area += 0.5 * np.sum(q_old[:-1] * q_new[1:] - q_old[1:] * q_new[:-1])
        q_old = q_new
    return area / (steps * dt)
