# Public reproduction kit — corrected (Rev.3 correction)

Additive directory. Nothing under `validation/mfd_reproduction_rev3/` or elsewhere in this repository was modified.

## Relationship to the already-published kit
`validation/mfd_reproduction_rev3/reproduction/repro_kit/` (published in commit ffa8437) keeps, unmodified, three hash lists
(`KIT_MANIFEST_sha256.txt`, `expected_evidence_sha256.txt`, `evidence_input/SHA256SUMS.txt`) that still list five
authorization-process records which are intentionally not published. As a result its own input check
(`tools/verify_inputs.py`) reports those five as absent and exits non-zero, and one unit test removes a file that is not there.
That earlier kit is left as is; its limitation is documented here.

## What this corrected kit changes (`repro_kit_public/`)
Only three files differ from the published kit:
1. `expected_evidence_sha256.txt` – lists the 18 public evidence files only.
2. `evidence_input/SHA256SUMS.txt` – lists the 17 public evidence files (itself is the 18th).
3. `code/tests/test_analysis.py` – the "missing file is detected" fixture removes `T3-DT01_execution_manifest.json`
   instead of an unpublished file (the test still checks the same behavior). Analysis code is unchanged.
`KIT_MANIFEST_sha256.txt` is regenerated for the public tree (37 files). The internal manifests were not changed.

## What is and is not verified
- Verified here: byte integrity of the 18 public evidence files against the in-bundle list (self-referential, not an independent
  root of trust); 19 unit tests; ledger consistency of the 140 classification comparisons (69 MATCH / 71 PARTIAL / 0 MISMATCH).
- NOT verified (and reported as such by the analysis output): HMAC authenticity, approval state, Gate B missing inputs,
  independent third-party execution. The five unpublished records are not treated as verified; see `EXCLUDED_INTERNAL_5.md`.
- G4 remains HOLD. Technical collation is not a formal verification status.

## Run
Python ≥3.11 with NumPy: `cd repro_kit_public && bash run_all.sh python3 myrun`. Exit 0 = all steps succeeded.
Saved run of the maintainers: `verification_run/` (see `PUBLIC_VERIFICATION_REPORT.md`). No new simulation is performed.
