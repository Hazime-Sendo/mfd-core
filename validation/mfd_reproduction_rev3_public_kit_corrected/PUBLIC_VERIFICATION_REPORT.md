# Public verification run report
Environment: Python 3.13.18, NumPy 2.5.3, Linux x86_64 (see verification_run/logs/public_run1_env.txt).
Command: `bash run_all.sh python3 public_run1` inside `repro_kit_public/` (copy as committed). Exit code 0.
- Environment check: OK. Input hashes: 18 files, 0 mismatch, 0 extra. Tests: Ran 19, OK. Evidence unchanged before/after. Stop conditions: none.
- Analysis: 140 classification comparisons: MATCH 69, PARTIAL 71, MISMATCH 0; cross-inconsistent 0.
- Output hashes: analysis_report.json 812f708b…cef1, label_reconstruction_140.json b0f3536a…10c9e (see logs/public_run1_outputs_sha256.txt).
- Not verified: HMAC authenticity, approval state, Gate B missing inputs, independent third-party run.
No new simulation; bit-wise claims limited to the confirmed environment (Python 3.13 / NumPy 2.5 / SciPy 1.18).
