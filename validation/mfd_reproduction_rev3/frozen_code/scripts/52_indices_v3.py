# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""Arrival-time indices and energy-based terminal classes of specification v3 (docs/stage3_main_spec_v3.md, Sec. 2-3).
All indices are online hold-based (window h). Unreached -> None (censored at observation end by the caller)."""
import numpy as np
Q_MIN, R_THR, U_THR, G_TOL, G2 = 0.9, 0.5, 0.1, 1e-2, 0.1

def first_run(t, ok, h):
    """first t_det such that ok holds for all samples with time in [t_det-h, t_det] (t sorted, max sample gap <= h assumed); returns t_det or None"""
    t = np.asarray(t, float); ok = np.asarray(ok, bool); start = None
    for j in range(len(ok)):
        if ok[j]:
            if start is None: start = t[j]
            if t[j] - start >= h - 1e-9: return float(t[j])
        else: start = None
    return None

def indices(tf, Q, rn, rm, U, G, dt, h=5.0):
    """tf frame times; U[i] at time i*dt; G[i] at time i*dt (len may be len(U)-1). Returns dict of t_det and arrival (=t_det-h)."""
    n = len(G); ts = np.arange(n) * dt; Us = np.asarray(U)[:n]; L = int(round(h / dt))
    Uf = np.asarray(U)[np.minimum(np.round(np.asarray(tf) / dt).astype(int), len(U) - 1)]
    m = np.minimum(rn, rm); c1p = (Q >= Q_MIN) & (m <= R_THR); c1e = c1p & (Uf <= U_THR)
    # windowed gradient max for O2' (window [i-L, i])
    gm = np.full(n, np.inf)
    if n > L: gm[L:] = np.lib.stride_tricks.sliding_window_view(np.asarray(G, float), L + 1).max(axis=1)
    ok2 = np.zeros(n, bool); ok2[L:] = (gm[L:] <= G2) & ((Us[:-L] - Us[L:]) <= U_THR) if n > L else ok2[L:]
    fi = np.minimum(np.round(np.asarray(tf) / dt).astype(int), n - 1)
    # O3: O1' window satisfied at frame j AND O2' holds at that time -> evaluate by marking frames where O1' hold complete
    def hold_flags(ok):
        out = np.zeros(len(ok), bool); start = None
        for j in range(len(ok)):
            if ok[j]:
                if start is None: start = tf[j]
                out[j] = (tf[j] - start) >= h - 1e-9
            else: start = None
        return out
    f1p, f1e = hold_flags(c1p), hold_flags(c1e)
    o3 = np.where(f1p & ok2[fi])[0]
    d = dict(O1p=first_run(tf, c1p, h), O1E=first_run(tf, c1e, h), tE=first_run(ts, Us <= U_THR, h), tG=first_run(ts, np.asarray(G) <= G_TOL, h),
             O2p=first_run(ts, ok2, 0.0), O3=float(tf[o3[0]]) if len(o3) else None)
    first = np.where(f1p)[0]; d['chir'] = None if not len(first) else ('native' if rn[first[0]] <= rm[first[0]] else 'mirror')
    return {k: (v if k == 'chir' else v) for k, v in d.items()}

def final_class(conv, U_end, m_end, rn_end, rm_end, anomaly, thr=U_THR):
    """exactly one of native / mirror / stagnation / unconverged / other (spec v3 Sec. 3)"""
    if anomaly: return 'other'
    if not conv: return 'unconverged'
    if U_end > thr: return 'stagnation'
    if m_end <= R_THR: return 'native' if rn_end <= rm_end else 'mirror'
    return 'other'

def grad_converged_end(G, dt, h=5.0):
    L = int(round(h / dt)); return len(G) >= L and float(np.max(np.asarray(G)[-L:])) <= G_TOL
