#!/usr/bin/env python3
"""Layer III scientific-equivalence check: python tools/layer3_canonical_check.py LAYER3_KIT_DIR OUT_DIR
Compares OUT_DIR/label_reconstruction_140.json and OUT_DIR/analysis_report.json with the stored expectations in LAYER3_KIT_DIR/expected/
using tools/canonical_compare.py. The comparison is structured (see NORMALIZATION_SPEC.md); the byte hash of the stored original is checked separately."""
import os, sys
kit, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
sys.path.insert(0, os.path.join(kit, "tools"))
import canonical_compare as cc
ok = True
try:
    el = cc.load_strict(os.path.join(kit, "expected", "label_reconstruction_140.json")); al = cc.load_strict(os.path.join(out, "label_reconstruction_140.json"))
    er = cc.load_strict(os.path.join(kit, "expected", "analysis_report_expected.json")); ar = cc.load_strict(os.path.join(out, "analysis_report.json"))
except (cc.InvalidJSON, OSError, ValueError) as ex:
    print("INVALID OR MISSING INPUT:", ex); sys.exit(3)
P, info = cc.compare_labels(el, al)
print("labels: records expected/actual %s/%s, order identical %s" % (info.get("n_expected"), info.get("n_actual"), info.get("order_identical")))
print("labels: canonical sha256 (not a file hash): expected %s actual %s" % (cc.canonical_sha256(el)[:16], cc.canonical_sha256(al)[:16]))
for p in P[:20]: print("  DIFF", p)
print("labels:", "EQUIVALENT" if not P else "NOT EQUIVALENT (%d)" % len(P)); ok &= not P
P2 = cc.compare_report(er, ar)
for p in P2[:20]: print("  DIFF", p)
print("report: %s (rtol %g; 'environment' block excluded)" % ("EQUIVALENT" if not P2 else "NOT EQUIVALENT (%d)" % len(P2), cc.REPORT_RTOL)); ok &= not P2
sys.exit(0 if ok else 1)
