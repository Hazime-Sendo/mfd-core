# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""Stage 3 run code, specification v3 (docs/stage3_main_spec_v3.md). Dynamics identical to scripts/22, 30, 41.
v3 changes: DT is a parameter (all time-based constants in time units), conditional extension (+10..+40 tu until grad-converged,
then up to +100 tu only for runs still unconverged), per-step gnorm/U stored, trace_fixed with per-step gnorm."""
import os, sys, json, time
import numpy as np
from collections import deque
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'src'))
from metriplectic_folding import GoLandscape, CapMob, CirMob, FoldDiag, make_native, kabsch_rmsd
from mfd_discrete_gradient import dg_step, I3
N, T_MAX, G_TOL, HOLD = 20, 100.0, 1e-2, 5.0
def init_chain(seed):
    rng = np.random.default_rng(seed)
    return np.c_[np.arange(N, dtype=float), np.zeros((N, 2))] + 0.1 * rng.normal(size=(N, 3))

def trace_run(ns, a, seed, D_MAX, DT=5e-3):
    k = lambda tu: int(round(tu / DT))
    MAX_STEPS, EVERY, REC, RING, POST = k(T_MAX), k(0.1), k(0.025), k(0.5), k(2.0)
    EXT_MIN, EXT_40, EXT_100, WG = k(10), k(40), k(100), k(HOLD)
    x_nat = make_native(N, ns); x = init_chain(seed)
    land, cap, cir = GoLandscape(x_nat), CapMob(N), CirMob(N, a)
    diag = FoldDiag(land, x_nat, window=max(10, int(1.0 / DT)), hold=5)
    x_mir = x_nat * np.array([-1.0, 1.0, 1.0])
    Ux, grad = land.energy_grad(x)
    U_hist, rate_ratio, clip_time = [Ux], [], 0.0
    Dh, Gh, Sh = [], [], []
    fr = {}; ring = deque(maxlen=RING); dense_until = POST - 1; s_prev = 1.0
    orig_end = None; t_detect = None; ext_min_stop = ext40 = ext100 = None; grad_converged = False; beyond40 = False; t = -1
    def add(step, x32, dense):
        if step in fr: return
        xd = x32.astype(float)
        fr[step] = (x32, land.Q(xd), kabsch_rmsd(xd, x_nat), kabsch_rmsd(xd, x_mir), dense)
    for t in range(MAX_STEPS + EXT_100):
        in_orig = orig_end is None
        M3 = np.kron(np.diag(cap.g) + cir.matrix(cap.g), I3)
        D = float(np.sum(grad * (cap.g[:, None] * grad)))
        s = min(1.0, D_MAX / D) if D > 0 else 1.0
        Dh.append(D); Gh.append(float(np.linalg.norm(grad)))      # Euclidean norm, as in v2
        for _ in range(4):
            out = dg_step(land, M3, x, Ux, DT * s)
            rate = (Ux - out[1]) / DT
            if rate <= D_MAX * 1.001: break
            s *= D_MAX / rate
        Sh.append(s)
        x, Ux = out; grad = land.energy_grad(x)[1]
        cap.relax(land.local_Q(x), DT)
        U_hist.append(Ux); rate_ratio.append(rate / D_MAX)
        x32 = x.astype(np.float32)
        if s >= 0.999 and s_prev < 0.999:
            for tt, xx in ring: add(tt, xx, True)
            dense_until = max(dense_until, t + POST)
        s_prev = s
        if t <= dense_until: add(t, x32, True)
        elif t % REC == 0: add(t, x32, False)
        ring.append((t, x32))
        if in_orig:
            diag.record(Ux, s < 0.999); clip_time += DT * (s < 0.999)
            if (t % EVERY == 0 and diag.evaluate(x) in FoldDiag.TERMINAL) or t == MAX_STEPS - 1:
                orig_end = t; t_detect = (t + 1) * DT; ext_min_stop, ext40, ext100 = t + EXT_MIN, t + EXT_40, t + EXT_100
        else:
            if t >= ext_min_stop and max(Gh[-WG:]) <= G_TOL: grad_converged = True; break
            if t >= ext40: beyond40 = True
            if t >= ext100: break
    U = np.array(U_hist); steps = np.array(sorted(fr))
    summ = dict(native_seed=ns, a=a, seed=seed, D_max=D_MAX, DT=DT, state=diag.state, t=t_detect, clip_time=clip_time, U0=float(U[0]),
                orig_end_step=int(orig_end), total_steps=int(t + 1), t_end=(t + 1) * DT, U_at_detect=float(U[orig_end + 1]), U_end=float(U[-1]),
                max_dU=float(np.diff(U).max()), max_rate_ratio=float(max(rate_ratio)),
                grad_converged=bool(grad_converged), extended_beyond_40=bool(beyond40), ext_tu=(t - orig_end) * DT, gnorm_end=float(Gh[-1]),
                n_frames=int(len(steps)), n_dense=int(sum(fr[q][4] for q in fr)))
    arrays = dict(U=U, D_inst=np.array(Dh, np.float32), gnorm=np.array(Gh, np.float32), s=np.array(Sh, np.float32),
                  frame_step=steps, frame_x=np.array([fr[q][0] for q in steps]), frame_Q=np.array([fr[q][1] for q in steps], np.float32),
                  frame_rmsd_nat=np.array([fr[q][2] for q in steps], np.float32), frame_rmsd_mir=np.array([fr[q][3] for q in steps], np.float32),
                  frame_dense=np.array([fr[q][4] for q in steps]), x_final=x, g_final=cap.g.copy())
    return summ, arrays

def trace_fixed(ns, a, seed, D_MAX, dt, T, frame_dt=0.025):
    """fixed-length run without FoldDiag; frames (x, Q, rmsd_nat, rmsd_mir) on a fixed time grid; per-step U and |grad|_2"""
    x_nat = make_native(N, ns); x = init_chain(seed); x_mir = x_nat * np.array([-1.0, 1.0, 1.0])
    land, cap, cir = GoLandscape(x_nat), CapMob(N), CirMob(N, a)
    Ux, grad = land.energy_grad(x); U = [Ux]; G = []; clip = 0.0; ft, fQ, fn, fm = [], [], [], []
    nsteps = int(round(T / dt)); fk = int(round(frame_dt / dt))
    for t in range(nsteps):
        M3 = np.kron(np.diag(cap.g) + cir.matrix(cap.g), I3)
        D = float(np.sum(grad * (cap.g[:, None] * grad)))
        s = min(1.0, D_MAX / D) if D > 0 else 1.0
        G.append(float(np.linalg.norm(grad)))
        for _ in range(4):
            out = dg_step(land, M3, x, Ux, dt * s)
            rate = (Ux - out[1]) / dt
            if rate <= D_MAX * 1.001: break
            s *= D_MAX / rate
        x, Ux = out; grad = land.energy_grad(x)[1]
        cap.relax(land.local_Q(x), dt); U.append(Ux); clip += dt * (s < 0.999)
        if (t + 1) % fk == 0:
            ft.append((t + 1) * dt); fQ.append(land.Q(x)); fn.append(kabsch_rmsd(x, x_nat)); fm.append(kabsch_rmsd(x, x_mir))
    return dict(U=np.array(U), gnorm=np.array(G), clip=clip, t=np.array(ft), Q=np.array(fQ), rn=np.array(fn), rm=np.array(fm), x_final=x, dt=dt)

def job(args):
    ns, a, D, seed, DT, outdir = args
    name = f"ns{ns}_a{a}_D{int(D)}_dt{DT:g}_s{seed}.npz"
    t0 = time.time(); summ, arr = trace_run(ns, a, seed, D, DT); wall = time.time() - t0
    path = os.path.join(outdir, 'traj', name); np.savez_compressed(path, **arr)
    summ['file'] = name; summ['wall_s'] = round(wall, 2); summ['bytes'] = os.path.getsize(path)
    return summ
