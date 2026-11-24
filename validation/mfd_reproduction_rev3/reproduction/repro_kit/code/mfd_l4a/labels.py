"""A3 Label Reconstruction. Independent re-implementation of the rules read from frozen 52_indices_v3.py (final_class) and Rev.3 8B.1.
Arrival state E_theta and structural class y_theta are stored in separate fields."""
THETAS = (0.01, 0.03, 0.1, 0.3)
R_THR = 0.5

def arrival_state(U_end, grad_converged, theta):
    if U_end <= theta: return "ARRIVED"
    return "STAGNANT" if grad_converged else "CENSORED"

def structural_class(conv, U_end, m_end, rn_end, rm_end, anomaly, theta):
    """mirrors frozen final_class; m_end/rn/rm may be None -> returns (None,'NOT ESTIMABLE: m_end unavailable') only when the branch needs them"""
    if anomaly: return "other", ""
    if not conv: return "unconverged", ""
    if U_end > theta: return "stagnation", ""
    if m_end is None: return None, "m_end/rn/rm unavailable (needs NPZ frame arrays)"
    if m_end <= R_THR: return ("native" if rn_end <= rm_end else "mirror"), ""
    return "other", ""

import math
def ledger_anomaly(s):
    """same expression as frozen controller (mfd_rbsh_v2_controller.py:164): not finite(U_end) or max_dU > 1e-9*max(1,|U0|)"""
    return (not math.isfinite(s["U_end"])) or s["max_dU"] > 1e-9 * max(1.0, abs(s["U0"]))

def reconstruct(rows, npz_loader=None):
    """rows: ledger rows. npz_loader(key)->dict or None. Returns list of per-(trial,theta) records."""
    out = []
    for r in rows:
        s = r["summary"]; conv = bool(s["grad_converged"]); Ue = s["U_end"]; anom = ledger_anomaly(s)
        m_end = rn = rm = None; src = "ledger"
        arr = npz_loader(r["key"]) if npz_loader else None
        if arr is not None:
            rn = float(arr["frame_rmsd_nat"][-1]); rm = float(arr["frame_rmsd_mir"][-1]); m_end = min(rn, rm); src = "ledger+npz(last frame)"
        for th in THETAS:
            E = arrival_state(Ue, conv, th)
            y, why = structural_class(conv, Ue, m_end, rn, rm, anom, th)
            exp = r["classes"][str(th)]
            if y is None:
                # partial check: only the branch-independent facts can be compared
                cmp = "PARTIAL" if exp in ("native", "mirror", "other") else "MISMATCH"
                note = why
            else:
                cmp = "MATCH" if y == exp else "MISMATCH"; note = ""
            # E_theta vs ledger class cross-consistency (arrival must agree with stagnation/unconverged semantics)
            ok_cross = ((E == "STAGNANT") == (exp == "stagnation")) and ((E == "CENSORED") == (exp == "unconverged" and Ue > th))
            out.append(dict(key=r["key"], theta=th, E=E, y_rebuilt=y, y_ledger=exp, compare=cmp, cross_consistent=bool(ok_cross), source=src, note=note,
                            ledger_state=s["state"], chir=r["indices"]["chir"], anomaly=anom, anomaly_source="ledger summary (derived)"))
    return out

def summarize(recs):
    from collections import Counter
    return {"n": len(recs), "compare": dict(Counter(x["compare"] for x in recs)),
            "cross_inconsistent": sum(1 for x in recs if not x["cross_consistent"]),
            "crosstab_E_y_ledger": {"%s|%s" % k: v for k, v in sorted(Counter((x["E"], x["y_ledger"]) for x in recs).items())}}
