import os, sys, json, shutil, tempfile, hashlib, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mfd_l4a.evidence import Evidence, EvidenceError, sha256_file
from mfd_l4a import labels, threshold_time as tt, dt_compare as dc, provenance
import run_analysis
EV = os.environ.get("EVIDENCE_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "evidence_input")

def tree_hash(d):
    return {n: sha256_file(os.path.join(d, n)) for n in sorted(os.listdir(d))}

class Known(unittest.TestCase):
    def test_first_hold(self):
        t = np.arange(0, 20, 0.5); ok = t >= 7.0
        det, start = tt.first_hold(t, ok); self.assertEqual((det, start), (12.0, 7.0))
    def test_censored_not_filled(self):
        r = tt.t_theta(np.array([5.0, 4.0, 3.0]), 1.0, 0.1, 1); self.assertIsNone(r["T"]); self.assertTrue(r["status"].startswith("RIGHT_CENSORED"))
    def test_hold_incomplete(self):
        U = np.array([5.0] * 5 + [0.0] * 3); r = tt.t_theta(U, 1.0, 0.1, 1); self.assertEqual(r["status"], "RIGHT_CENSORED_HOLD_INCOMPLETE")
    def test_arrival_states(self):
        self.assertEqual(labels.arrival_state(0.05, True, 0.1), "ARRIVED"); self.assertEqual(labels.arrival_state(0.05, False, 0.1), "ARRIVED")
        self.assertEqual(labels.arrival_state(0.5, True, 0.1), "STAGNANT"); self.assertEqual(labels.arrival_state(0.5, False, 0.1), "CENSORED")
    def test_structural_rule(self):
        f = labels.structural_class
        self.assertEqual(f(True, .5, .1, .1, .2, False, .1)[0], "stagnation"); self.assertEqual(f(True, .05, .4, .3, .4, False, .1)[0], "native")
        self.assertEqual(f(True, .05, .4, .5, .4, False, .1)[0], "mirror"); self.assertEqual(f(True, .05, .9, .9, .95, False, .1)[0], "other")
        self.assertEqual(f(False, .05, .4, .3, .4, False, .1)[0], "unconverged"); self.assertEqual(f(True, .05, .4, .3, .4, True, .1)[0], "other")
        self.assertIsNone(f(True, .05, None, None, None, False, .1)[0])
    def test_order(self):
        q = lambda h: 1.0 + 3.0 * h ** 2
        r = dc.order_from_three(q(.4), q(.2), q(.1)); self.assertAlmostEqual(r["p_hat"], 2.0, places=9)
        self.assertEqual(dc.order_from_three(1, 1, 1)["status"], "INCONCLUSIVE")
    def test_kabsch(self):
        P = np.random.default_rng(0).normal(size=(20, 3)); th = .7; R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
        self.assertLess(dc.kabsch_rmsd(P, P @ R.T + 3), 1e-12)
        M = P * np.array([1, 1, -1]); self.assertGreater(dc.kabsch_rmsd(P, M), 1e-3); self.assertLess(dc.kabsch_rmsd(P, M, True), 1e-12)

@unittest.skipUnless(os.path.isdir(EV), "evidence copy missing")
class Evidence_(unittest.TestCase):
    def test_real_integrity_and_labels(self):
        ev = Evidence(EV); self.assertTrue(all(r.integrity in ("OK", "REFERENCE_FILE") for r in ev.records.values()))
        rows = ev.load_jsonl("ledger_dt0025.jsonl") + ev.load_jsonl("ledger_dt00125.jsonl"); self.assertEqual(len(rows), 35)
        rec = labels.reconstruct(rows, lambda k: ev.load_npz(k + ".npz") if k + ".npz" in ev.records else None)
        self.assertEqual(len(rec), 140); self.assertFalse([x for x in rec if x["compare"] == "MISMATCH" or not x["cross_consistent"]])
    def test_no_write_to_evidence(self):
        before = tree_hash(EV); out = tempfile.mkdtemp(); run_analysis.main(EV, out); self.assertEqual(before, tree_hash(EV)); shutil.rmtree(out)
    def test_refuse_output_inside_evidence(self):
        with self.assertRaises(SystemExit): run_analysis.main(EV, os.path.join(EV, "out"))
    def test_hash_mismatch_detected(self):
        d = tempfile.mkdtemp(); shutil.copytree(EV, d + "/e"); os.chmod(d + "/e", 0o755)
        p = d + "/e/ledger_dt00125.jsonl"; os.chmod(p, 0o644)
        with open(p, "a") as fh: fh.write(" ")
        ev = Evidence(d + "/e"); self.assertEqual(ev.records["ledger_dt00125.jsonl"].integrity, "HASH_MISMATCH")
        with self.assertRaises(EvidenceError): ev.load_jsonl("ledger_dt00125.jsonl")
        shutil.rmtree(d, ignore_errors=True)
    def test_missing_file_detected(self):
        d = tempfile.mkdtemp(); shutil.copytree(EV, d + "/e"); os.chmod(d + "/e", 0o755); os.remove(d + "/e/T3-DT01_execution_manifest.json")
        ev = Evidence(d + "/e"); self.assertEqual(ev.records["T3-DT01_execution_manifest.json"].integrity, "MISSING"); shutil.rmtree(d, ignore_errors=True)
    def test_missing_sums_file(self):
        d = tempfile.mkdtemp(); shutil.copytree(EV, d + "/e"); os.chmod(d + "/e", 0o755); os.remove(d + "/e/SHA256SUMS.txt")
        with self.assertRaises(EvidenceError): Evidence(d + "/e")
        shutil.rmtree(d, ignore_errors=True)
    def test_label_mismatch_injection_detected(self):
        ev = Evidence(EV); rows = ev.load_jsonl("ledger_dt0025.jsonl")
        r = json.loads(json.dumps(rows[0])); r["classes"]["0.1"] = "native"   # inject: ledger says native although stagnant
        rec = labels.reconstruct([r]); self.assertTrue([x for x in rec if x["compare"] == "MISMATCH" or not x["cross_consistent"]])
    def test_provenance_not_upgraded(self):
        p = provenance.assess(Evidence(EV)); self.assertEqual(p["byte_integrity"]["state"], "VERIFIED")
        for k in ("hmac_authenticity", "approval_state", "gate_b_missing_inputs"): self.assertEqual(p[k]["state"], "NOT VERIFIED")
        self.assertTrue(all(len(v) == 0 for v in p["gate_b_missing_inputs"]["matches_in_bundle"].values()))
    def test_dt_pair_not_estimable_fields(self):
        ev = Evidence(EV); rows = {r["key"]: r for r in ev.load_jsonl("ledger_dt0025.jsonl") + ev.load_jsonl("ledger_dt00125.jsonl")}
        kc, kf = "ns15_a8_D500_dt0.0025_s0", "ns15_a8_D500_dt0.00125_s0"
        r = dc.pair(rows[kc], ev.load_npz(kc + ".npz"), rows[kf], ev.load_npz(kf + ".npz"))
        self.assertTrue(r["convergence_order"].startswith("NOT ESTIMABLE")); self.assertTrue(r["clip_time"]["bound_N_b_DT_c"].startswith("NOT ESTIMABLE"))
        self.assertGreater(r["common_time_U"]["n_common"], 100); self.assertLess(r["common_time_U"]["max_rel"], 2e-3)

class V2(unittest.TestCase):
    def test_stride_design_rule(self):
        self.assertEqual(tt.infer_stride(12121, 607, 0.0025), 20); self.assertEqual(tt.infer_stride(24161, 605, 0.00125), 40)
        self.assertEqual(tt.infer_stride(12120, 607, 0.0025), 20)      # total_steps divisible by stride: old formula returned None
        self.assertIsNone(tt.infer_stride(12121, 606, 0.0025)); self.assertIsNone(tt.infer_stride(1000, 21, 0.003))
    def test_anomaly_from_ledger(self):
        s = dict(U_end=1.0, max_dU=1e-3, U0=2447.0); self.assertTrue(labels.ledger_anomaly(s)); s["max_dU"] = -1e-12; self.assertFalse(labels.ledger_anomaly(s))
        self.assertTrue(labels.ledger_anomaly(dict(U_end=float("nan"), max_dU=0.0, U0=1.0)))
        rows = [dict(key="k", spec={}, summary=dict(grad_converged=True, U_end=0.05, max_dU=1e-3, U0=2447.0, state="NATIVE"), indices=dict(chir="native"), classes={"0.01": "other", "0.03": "other", "0.1": "other", "0.3": "other"})]
        self.assertTrue(all(x["compare"] == "MATCH" and x["y_rebuilt"] == "other" for x in labels.reconstruct(rows)))
    def test_label_counts_unchanged(self):
        if not os.path.isdir(EV): self.skipTest("no evidence")
        ev = Evidence(EV); rows = ev.load_jsonl("ledger_dt0025.jsonl") + ev.load_jsonl("ledger_dt00125.jsonl")
        rec = labels.reconstruct(rows, lambda k: ev.load_npz(k + ".npz") if k + ".npz" in ev.records else None)
        s = labels.summarize(rec)["compare"]; self.assertEqual((s.get("MATCH"), s.get("PARTIAL"), s.get("MISMATCH", 0)), (69, 71, 0)); self.assertFalse(any(x["anomaly"] for x in rec))

if __name__ == "__main__": unittest.main(verbosity=2)
