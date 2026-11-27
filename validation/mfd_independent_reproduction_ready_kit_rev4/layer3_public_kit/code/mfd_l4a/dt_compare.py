"""A5 DT Comparison Analyzer (descriptive statistics only; no pass/fail on absolute thresholds - those remain provisional).
Single-pair agreement and >=3-level convergence order are reported separately; <3 levels -> order NOT ESTIMABLE."""
import numpy as np
from .threshold_time import infer_stride

def kabsch_rmsd(P, Q, allow_reflection=False):
    P = P - P.mean(0); Q = Q - Q.mean(0)
    H = P.T @ Q; U, S, Vt = np.linalg.svd(H); d = np.sign(np.linalg.det(Vt.T @ U.T))
    if allow_reflection: d = 1.0
    D = np.diag([1, 1, d]); R = Vt.T @ D @ U.T
    return float(np.sqrt(np.mean(np.sum((P @ R.T - Q) ** 2, axis=1))))

def pair(rowc, arrc, rowf, arrf):
    """coarse (DT_c) vs fine (DT_f=DT_c/2). Returns dict of reported quantities with explicit NOT ESTIMABLE where inputs are missing."""
    sc, sf = rowc["summary"], rowf["summary"]; DTc, DTf = rowc["spec"]["DT"], rowf["spec"]["DT"]
    out = {"key_coarse": rowc["key"], "key_fine": rowf["key"], "DT_c": DTc, "DT_f": DTf}
    norm = sc["U0"] - sc["U_end"]
    out["endpoint"] = {"U_end_diff": abs(sc["U_end"] - sf["U_end"]), "t_end_c": sc["t_end"], "t_end_f": sf["t_end"], "dt_end": abs(sc["t_end"] - sf["t_end"]),
                       "note": "endpoints are at different physical times when t_end differs"}
    stc, stf = infer_stride(sc["total_steps"], len(arrc["U_every10"]), DTc), infer_stride(sf["total_steps"], len(arrf["U_every10"]), DTf)
    if stc is None or stf is None:
        out["common_time_U"] = "NOT ESTIMABLE (stride)"
    else:
        tc = np.arange(len(arrc["U_every10"])) * stc * DTc; tf = np.arange(len(arrf["U_every10"])) * stf * DTf
        # common grid points: match by rounded time in 1e-9 units
        kc = {int(round(t * 1e9)): i for i, t in enumerate(tc)}; common = [(kc[int(round(t * 1e9))], j) for j, t in enumerate(tf) if int(round(t * 1e9)) in kc]
        if len(common) < 10: out["common_time_U"] = "NOT ESTIMABLE (too few common times)"
        else:
            ic = np.array([c for c, _ in common]); jf = np.array([f for _, f in common])
            d = np.abs(arrc["U_every10"][ic] - arrf["U_every10"][jf]) / norm
            out["common_time_U"] = {"n_common": len(common), "max_rel": float(d.max()), "rms_rel": float(np.sqrt(np.mean(d ** 2))), "t_of_max": float(tc[ic][d.argmax()]),
                                    "normalisation": "U0-U_end (coarse)"}
    # structure at endpoint (x_final) and frame RMSD-to-reference differences on common frame times
    xc, xf = arrc["x_final"], arrf["x_final"]
    out["x_final_rmsd"] = {"SO3": kabsch_rmsd(xc, xf), "with_reflection": kabsch_rmsd(xc, xf, True), "note": "endpoints may be at different times"}
    fc = {int(round(s * DTc * 1e9)): i for i, s in enumerate(arrc["frame_step"])}; cm = [(fc[int(round(s * DTf * 1e9))], i) for i, s in enumerate(arrf["frame_step"]) if int(round(s * DTf * 1e9)) in fc]
    if cm:
        ci = np.array([c for c, _ in cm]); fi = np.array([f for _, f in cm])
        out["frames_common"] = {"n": len(cm), "max_abs_d_rmsd_nat": float(np.abs(arrc["frame_rmsd_nat"][ci] - arrf["frame_rmsd_nat"][fi]).max()),
            "max_abs_d_rmsd_mir": float(np.abs(arrc["frame_rmsd_mir"][ci] - arrf["frame_rmsd_mir"][fi]).max()),
            "max_abs_d_gnorm": float(np.abs(arrc["gnorm_at_frames"][ci].astype(float) - arrf["gnorm_at_frames"][fi].astype(float)).max()),
            "note": "RMSD-to-native/mirror differences are a proxy; trajectory-to-trajectory Kabsch needs frame_x, which is not stored in these NPZ files"}
    else: out["frames_common"] = "NOT ESTIMABLE (no common frame times)"
    out["clip_time"] = {"coarse": sc["clip_time"], "fine": sf["clip_time"], "abs_diff": abs(sc["clip_time"] - sf["clip_time"]),
        "bound_N_b_DT_c": "NOT ESTIMABLE (step array s[k] not stored; N_b unknown)", "t_first_clip_diff": "NOT ESTIMABLE (s[k] not stored)",
        "inside_outside_window": "NOT ESTIMABLE (clipping window needs s[k])"}
    out["convergence_order"] = "NOT ESTIMABLE (2 DT levels only; >=3 required)"
    return out

def order_from_three(q_h, q_h2, q_h4, floor=0.0):
    """Q at DT, DT/2, DT/4 -> e1,e2,p. Returns INCONCLUSIVE if either difference is below 10x noise floor."""
    e1, e2 = abs(q_h - q_h2), abs(q_h2 - q_h4)
    if min(e1, e2) < 10 * floor or e2 == 0: return {"status": "INCONCLUSIVE", "e1": e1, "e2": e2}
    return {"status": "ESTIMATED", "e1": e1, "e2": e2, "p_hat": float(np.log2(e1 / e2))}
