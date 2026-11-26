"""Tests of the Layer III canonical comparison (Rev.3). They show that data differing only in form is accepted
while scientific differences are rejected, and that the byte hash of the original is NOT replaced by the canonical hash."""
import os, sys, json, copy, hashlib, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(KIT, "tools"))
import canonical_compare as cc

EXP = os.path.join(KIT, "expected", "label_reconstruction_140.json")
RAW_SHA = "b0f3536ac809e4668cd3d9e0a50c43285753ee7bc41ac85f640660ffedb10c9e"

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(EXP, "rb") as fh: cls.raw = fh.read()
        cls.base = cc.loads_strict(cls.raw)
    def test_original_bytes_hash(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), RAW_SHA); self.assertEqual(len(self.base), 140)
    def test_identical(self):
        P, _ = cc.compare_labels(self.base, copy.deepcopy(self.base)); self.assertEqual(P, [])
    def test_key_order_only(self):
        alt = [dict(reversed(list(r.items()))) for r in self.base]
        P, _ = cc.compare_labels(self.base, alt); self.assertEqual(P, [])
        self.assertEqual(cc.canonical_sha256(self.base), cc.canonical_sha256(alt))
        self.assertNotEqual(json.dumps(self.base).encode(), json.dumps(alt).encode())  # bytes differ, data equal
    def test_whitespace_newline_only(self):
        txt = json.dumps(self.base, indent=4).replace("\n", "\r\n").encode("utf-8")
        txt = b"\xef\xbb\xbf" + txt
        alt = cc.loads_strict(txt); P, _ = cc.compare_labels(self.base, alt); self.assertEqual(P, [])
        self.assertNotEqual(hashlib.sha256(txt).hexdigest(), RAW_SHA)   # byte hash differs...
        self.assertEqual(cc.canonical_sha256(alt), cc.canonical_sha256(self.base))  # ...canonical equal; the two hashes are different things
    def test_record_order_reported_not_failed(self):
        alt = list(reversed(self.base)); P, info = cc.compare_labels(self.base, alt); self.assertEqual(P, []); self.assertFalse(info["order_identical"])
    def test_label_changed(self):
        alt = copy.deepcopy(self.base); alt[7]["y_rebuilt"] = "native" if alt[7]["y_rebuilt"] != "native" else "mirror"
        P, _ = cc.compare_labels(self.base, alt); self.assertTrue(any("y_rebuilt" in p for p in P))
    def test_required_field_missing(self):
        alt = copy.deepcopy(self.base); del alt[3]["compare"]
        P, _ = cc.compare_labels(self.base, alt); self.assertTrue(any("missing required field compare" in p for p in P))
    def test_record_missing(self):
        alt = copy.deepcopy(self.base); del alt[10]
        P, _ = cc.compare_labels(self.base, alt); self.assertTrue(any("record missing" in p for p in P)); self.assertTrue(any("139" in p for p in P))
    def test_record_duplicated(self):
        alt = copy.deepcopy(self.base); alt[11] = copy.deepcopy(alt[12])
        P, _ = cc.compare_labels(self.base, alt); self.assertTrue(any("duplicate record" in p for p in P))
    def test_wrong_type(self):
        alt = copy.deepcopy(self.base); alt[0]["anomaly"] = 0
        P, _ = cc.compare_labels(self.base, alt); self.assertTrue(P)
    def test_theta_changed(self):
        alt = copy.deepcopy(self.base); alt[0]["theta"] = alt[0]["theta"] * 1.0000001
        P, _ = cc.compare_labels(self.base, alt); self.assertTrue(P)
    def test_report_numeric_within_tolerance(self):
        a = {"x": [1.0, {"y": 2.5}], "environment": {"python": "A"}}; b = {"x": [1.0 + 1e-12, {"y": 2.5}], "environment": {"python": "B"}}
        self.assertEqual(cc.compare_report(a, b), [])
    def test_report_numeric_beyond_tolerance(self):
        a = {"x": [1.0, {"y": 2.5}]}; b = {"x": [1.0, {"y": 2.5 * (1 + 1e-6)}]}
        self.assertTrue(cc.compare_report(a, b))
    def test_report_missing_key(self):
        self.assertTrue(cc.compare_report({"a": 1, "b": 2}, {"a": 1}))
    def test_nonfinite_rejected(self):
        for s in ('{"a": NaN}', '{"a": Infinity}', '{"a": -Infinity}'):
            with self.assertRaises(cc.InvalidJSON): cc.loads_strict(s)
    def test_duplicate_object_key_rejected(self):
        with self.assertRaises(cc.InvalidJSON): cc.loads_strict('{"a": 1, "a": 2}')
    def test_null_is_a_value(self):
        a = {"v": None}; b = {"v": 0}
        self.assertTrue(cc.compare_report(a, b))

if __name__ == "__main__": unittest.main()
