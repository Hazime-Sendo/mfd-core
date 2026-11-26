"""Entry point. Usage: python3 -I run_analysis.py <evidence_dir> <out_dir>. out_dir must differ from and not be inside evidence_dir."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mfd_l4a.evidence import Evidence, EvidenceError
from mfd_l4a import provenance, labels, threshold_time as tt, dt_compare as dc, report as rp

def main(evd, out):
    evd, out = os.path.abspath(evd), os.path.abspath(out)
    if out == evd or out.startswith(evd + os.sep): raise SystemExit("STOP: output directory is inside evidence directory (write to evidence forbidden)")
    os.makedirs(out, exist_ok=True)
    ev = Evidence(evd); items = []; stop = []
    bad = [r.name for r in ev.records.values() if r.integrity in ("HASH_MISMATCH", "MISSING")]
    if bad: stop.append("hash mismatch / missing: %s" % bad)
    prov = provenance.assess(ev)
    rows = ev.load_jsonl("ledger_dt0025.jsonl") + ev.load_jsonl("ledger_dt00125.jsonl")
    keyed = {r["key"]: r for r in rows}
    npz = lambda k: ev.load_npz(k + ".npz") if (k + ".npz") in ev.records else None
    # arrays_sha256 vs NPZ file hash is a different quantity (content hash of arrays); only report presence
    recs = labels.reconstruct(rows, npz); summ = labels.summarize(recs)
    mism = [x for x in recs if x["compare"] == "MISMATCH" or not x["cross_consistent"]]
    if mism: stop.append("label reconstruction mismatch: %d" % len(mism))
    items.append(rp.item("A3 label reconstruction (E_theta/y_theta, 140 labels)", "REVIEW", "PARTIAL", "MATCH" if not mism else "MISMATCH",
        {"summary": summ, "note": "structural class branch (native/mirror/other) needs m_end: rebuilt only where NPZ present (4 trials); others PARTIAL (ledger-consistency only)"}))
    # A4
    t_rows = []
    for k, r in keyed.items():
        a = npz(k)
        if a is None: continue
        c = tt.compare_to_ledger(r, a)
        stride = tt.infer_stride(r["summary"]["total_steps"], len(a["U_every10"]), r["spec"]["DT"])
        c["T_theta"] = {str(th): tt.t_theta(a["U_every10"], r["spec"]["DT"], th, stride) for th in labels.THETAS} if stride else "NOT ESTIMABLE"
        t_rows.append(c)
    led_check = [(k, (r["indices"]["tE"] is not None) == (r["summary"]["U_end"] <= 0.1) and (r["indices"]["tE"] is None or 5.0 <= r["indices"]["tE"] <= r["summary"]["t_end"] + 1e-9)) for k, r in keyed.items()]
    nonvac = [c for c in t_rows if c["ledger_tE"] is not None]
    items.append(rp.item("A4 T_theta vs ledger indices.tE (theta=0.1)", "REVIEW", "PARTIAL" if nonvac else "NOT ESTIMABLE", "REVIEW" if nonvac else "NOT VERIFIED",
        {"ledger_only_check": {"n": len(led_check), "tE_set_iff_Uend_le_0.1_and_in_range": sum(1 for _, ok in led_check if ok), "failures": [k for k, ok in led_check if not ok]},
         "numeric_comparison": {"trials_with_npz": len(t_rows), "trials_with_ledger_tE_set": len(nonvac),
            "verdict": "NOT TESTABLE: 0 comparable pairs (ledger tE set AND U array present); absence of mismatch over an empty set is not a PASS" if not nonvac else "see rows", "comparable_pairs": len(nonvac)},
         "T_theta_rebuilt_rows": t_rows,
         "quantisation": "stored U array uses stride (not 10): grid=stride*DT (0.05 tu for both DT); T_theta resolution limited to this grid. The 18 trials with tE set have no stored U array."}))
    # A5
    pairs = []
    for a_ in (8.0, 16.0):
        kc = [k for k, r in keyed.items() if r["spec"]["a"] == a_ and r["spec"]["ns"] == 15 and r["spec"]["DT"] == 0.0025 and r["spec"]["seed"] == 0]
        kf = [k for k, r in keyed.items() if r["spec"]["a"] == a_ and r["spec"]["ns"] == 15 and r["spec"]["DT"] == 0.00125 and r["spec"]["seed"] == 0]
        if kc and kf and npz(kc[0]) is not None and npz(kf[0]) is not None:
            pairs.append(dc.pair(keyed[kc[0]], npz(kc[0]), keyed[kf[0]], npz(kf[0])))
    items.append(rp.item("A5 DT pair comparison (single pairs)", "REVIEW", "PARTIAL", "DESCRIPTIVE", {"pairs": pairs, "order": "NOT ESTIMABLE (2 levels)"}))
    items.append(rp.item("A2 provenance", "NOT VERIFIED", "PARTIAL", "NOT VERIFIED", prov))
    rep = {"title": "MFD L4-001 analysis-only report", "stop_conditions_triggered": stop, "status_vocabulary": rp.STATUSES,
           "evidence_files": ev.summary(), "evidence_zip_sha256": "b7c06db713...366f (as recorded in spec; not recomputed here)",
           "formulas": {"E_theta": "ARRIVED if U_end<=theta; STAGNANT if U_end>theta and grad_converged; CENSORED otherwise", "T_theta": "first hold-complete detection time minus h (h=5.0)",
                        "thresholds": list(labels.THETAS), "provisional_thresholds_adjusted": False},
           "items": items, "verified": ["byte integrity vs in-bundle SHA256SUMS", "ledger/E_theta/y_theta consistency (140 labels)"],
           "not_verified": ["HMAC authenticity", "approval state", "Gate B missing inputs", "independent third-party run"],
           "environment": rp.env_info(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mfd_l4a"))}
    rp.write_json(os.path.join(out, "analysis_report.json"), rep)
    rp.write_json(os.path.join(out, "label_reconstruction_140.json"), recs)
    return rep

if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2]); print("stop conditions:", r["stop_conditions_triggered"] or "none")
