#!/usr/bin/env bash
# MFD Independent Reproduction Ready Kit Rev.4 -- one-shot run (Linux / WSL2).  Usage: bash run_all_rev8.sh [python3] [run_name]
# Default behaviour: re-aggregation / re-classification of STORED data only. No new trajectory is generated; no simulation is run.
# Inputs are verified by SHA-256 before and after and are never written. All outputs go to ./runs/<run_name>/ .
# A run by the kit's producer is a "producer re-run", NOT an independent verification and NOT a third-party reproduction.
# Exit codes: 0 all ok / 1 a comparison or test failed / 3 input or manifest integrity failure / 5 analysis failed / 7 label output differs / 10 run name exists
export PYTHONDONTWRITEBYTECODE=1   # never write bytecode caches into the kit (they would be unregistered files)
set -u; PY="${1:-python3}"; TAG="${2:-run1}"; HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
OUT="$HERE/runs/$TAG"; [ -e "$OUT" ] && { echo "ERROR: $OUT exists; choose another run_name"; exit 10; }
mkdir -p "$OUT/logs" "$OUT/layer1_out" "$OUT/layer2_out"; RC0=0; RC1=0; RC2=0; RC3=0
{
echo "== env =="; "$PY" -c "import sys,platform,numpy;print(sys.version);print(platform.platform());print('numpy',numpy.__version__)"; "$PY" -m pip freeze 2>/dev/null | grep -i -E "^(numpy|scipy)==" > "$OUT/logs/pip_freeze_filtered.txt"
echo "== [0] kit integrity (manifests, state-based check) =="
"$PY" -I -B tools/verify_kit_manifest.py "$HERE" --json "$OUT/logs/manifest_check_before.json"; MRC=$?
[ "$MRC" -eq 0 ] || { echo "KIT MANIFEST CHECK NOT PASSED (rc=$MRC: 1=integrity problem, 2=environment/file state; do not treat as PASS)"; exit 3; }
echo "-- [0a] regression tests of the manifest verifier (synthetic mini-kits only; the real kit is not touched)"
"$PY" -I -B tools/test_verify_kit_manifest.py || { echo "VERIFIER REGRESSION TESTS FAILED"; exit 3; }
echo "== [0b] input hash checks =="
( cd layer1_300trial/data && sha256sum -c dmax_sweep_runs.jsonl.sha256 ) || { echo "LAYER I INPUT HASH MISMATCH"; exit 3; }
( cd layer2_33traj && sha256sum -c SHA256SUMS_layer2.txt >/dev/null ) || { echo "LAYER II INPUT HASH MISMATCH"; exit 3; }
echo "== [1] Layer I: 300 trials (clip ratio, seed-block bootstrap B=10000 seed 20261124) =="
"$PY" layer1_300trial/code/rev3_clip_and_bootstrap.py layer1_300trial/data/dmax_sweep_runs.jsonl "$OUT/layer1_out" || RC1=5
"$PY" tools/check_layer1_expected.py "$OUT/layer1_out" expected/layer1_expected.json || RC1=1
echo "== [2] Layer II: 33 trajectories (21 with containers; 12 ledger-only) =="
( cd layer2_33traj/06_VERIFY && "$PY" -I -B mfd_independent_verify.py --ledger ../ledgers/ledger_dt0025.jsonl --full-dir ../03_B_FULL --tier1-dir ../04_B_TIER1 --out "$OUT/layer2_out/verify_raw.json" \
  && "$PY" -I -B extra_ns15_check.py ../../layer3_public_kit/evidence_input ../ledgers "$OUT/layer2_out/ns15_check.json" ) || RC2=5
"$PY" tools/layer2_summary.py "$OUT/layer2_out/verify_raw.json" "$OUT/layer2_out/ns15_check.json" || RC2=1
echo "== [3] Layer III: 36 tests (19 original + 17 canonical-comparison) + 140-label reconstruction, in a working copy =="
cp -r layer3_public_kit "$OUT/layer3_workcopy"
( cd "$OUT/layer3_workcopy" && bash run_all.sh "$PY" "$TAG" ); RC3=$?
L3="$OUT/layer3_workcopy"
echo "-- [3a] ORIGINAL INTEGRITY (byte level): raw SHA-256 of the produced label file vs the stored original expectation"
H=$(sha256sum "$L3/out_$TAG/label_reconstruction_140.json" | cut -d' ' -f1); echo "label_reconstruction_140.json sha256 $H"
if [ "$H" = "$(cut -d' ' -f1 "$HERE/layer3_public_kit/expected/label_reconstruction_140.json.sha256")" ]; then echo "RAW BYTES IDENTICAL TO ORIGINAL EXPECTATION"; else echo "RAW BYTES DIFFER (informational; see 3b for scientific equivalence)"; fi
echo "-- [3b] SCIENTIFIC EQUIVALENCE (structured, canonical comparison; see layer3_public_kit/NORMALIZATION_SPEC.md)"
"$PY" -I -B tools/layer3_canonical_check.py "$HERE/layer3_public_kit" "$L3/out_$TAG" || { echo "CANONICAL COMPARISON FAILED"; RC3=7; }
echo "== [4] per-trajectory asset matrix =="
"$PY" tools/build_layer2_asset_matrix.py "$HERE" "$L3/out_$TAG/label_reconstruction_140.json" "$OUT/layer2_out/verify_raw.json" "$OUT/layer2_out/ns15_check.json" "$OUT/layer2_out/MFD_LayerII_33_Trajectory_Asset_Matrix.csv"
echo "== [5] inputs unchanged (re-verification of all manifests) =="
"$PY" -I -B tools/verify_kit_manifest.py "$HERE" > "$OUT/logs/manifest_check_after.txt" 2>&1 && echo "KIT INPUTS UNCHANGED" || { echo "KIT CHANGED DURING RUN"; RC0=3; }
if [ "${STRICT_DIAG:-0}" = "1" ]; then echo "== [6] strict-mode diagnostics (optional, <=5 subprocess runs) =="; "$PY" -I -B tools/strict_mode_diagnostic.py "$OUT/logs/strict_mode_diagnostic.json" || true; fi
echo "== done: manifest rc=$RC0 layer1 rc=$RC1 layer2 rc=$RC2 layer3 rc=$RC3 =="
FIN=$RC0; for r in $RC3 $RC1 $RC2; do [ "$FIN" -eq 0 ] && FIN=$r; done; exit "$FIN"
} 2>&1 | tee "$OUT/logs/console.txt"
exit "${PIPESTATUS[0]}"
