"""A4 Threshold Time Analyzer. T_theta = (first hold-complete detection time) - h, per Rev.3 8B.1(2).
U_every10 (stored) is sampled every 10 steps, so reconstruction has grid resolution 10*DT; quantisation is reported separately from DT-to-DT differences.
Unreached -> right-censored; never filled with an estimate."""
import numpy as np
H = 5.0

def first_hold(t, ok, h=H):
    start = None
    for j in range(len(ok)):
        if ok[j]:
            if start is None: start = t[j]
            if t[j] - start >= h - 1e-9: return float(t[j]), float(start)
        else: start = None
    return None, None

def t_theta(U10, DT, theta, stride=10):
    t = np.arange(len(U10)) * DT * stride
    det, start = first_hold(t, np.asarray(U10) <= theta)
    if det is None:
        # distinguish: threshold never crossed vs crossed but hold not complete before end
        crossed = bool(np.any(np.asarray(U10) <= theta))
        return dict(status="RIGHT_CENSORED" if not crossed else "RIGHT_CENSORED_HOLD_INCOMPLETE", t_detect=None, T=None, t_end_grid=float(t[-1]))
    return dict(status="ARRIVED", t_detect=det, T=det - H, T_first_cross=start, grid=DT * stride)

def infer_stride(total_steps, n, DT=None):
    """Stored array = U[::stride], U has total_steps+1 samples, U[0]=U0 at t=0 (frozen controller: stride=round(0.05/DT)).
    Requires 0.05/DT to be an integer and n == total_steps//stride + 1; otherwise None (NOT ESTIMABLE)."""
    if DT is None: return None
    q = 0.05 / DT; stride = int(round(q))
    if stride < 1 or abs(q - stride) > 1e-9: return None
    return stride if n == total_steps // stride + 1 else None

def compare_to_ledger(row, arr):
    """compare theta=0.1 reconstruction with ledger indices.tE (t_detect) ; tolerance = one coarse grid step (10*DT) + DT"""
    DT = row["spec"]["DT"]; U = arr["U_every10"]
    stride = infer_stride(row["summary"]["total_steps"], len(U), DT)
    if stride is None: return dict(key=row["key"], verdict="NOT ESTIMABLE", reason="stride not integer")
    last_idx = (len(U) - 1) * stride   # last stored sample index; ledger U_end is index total_steps (may be later by < stride steps)
    if last_idx > row["summary"]["total_steps"] or abs(U[-1] - row["summary"]["U_end"]) > 1e-9 * max(1.0, abs(U[0])): return dict(key=row["key"], verdict="NOT ESTIMABLE", reason="time axis check failed")
    res = t_theta(U, DT, 0.1, stride)
    led = row["indices"]["tE"]; tol = (stride + 1) * DT
    if led is None and res["t_detect"] is None: v = "MATCH(both unreached)"
    elif led is None or res["t_detect"] is None: v = "MISMATCH"
    else: v = "MATCH" if abs(led - res["t_detect"]) <= tol else "MISMATCH"
    return dict(key=row["key"], ledger_tE=led, rebuilt_t_detect=res["t_detect"], stride=stride, grid=stride * DT, tol=tol, verdict=v, rebuilt=res)
