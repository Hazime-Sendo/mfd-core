# MFD Independent-Reproduction Materials (Rev.3, public-eligible subset)

This directory is an **additive** publication under `validation/`. No existing file of this repository
(including the top-level README, `.zenodo.json`, the 300-trial data and the `v1.0.0` tag) was changed.
License: this repository's existing license (Apache-2.0) applies.

## Layout
- `frozen_code/` – frozen verification code (`src/`, `scripts/`) as used for the checks.
- `verification/` – independent verification script, functional-check record, Claude construction verification.
- `data/B_FULL` (9 .m2), `data/B_TIER1` (10 .npz), `data/B_REGEN` (10 recipes, redacted log, pilot transcription).
- `reproduction/` – reproduction kit (`repro_kit/`) and provenance note. Run procedure: `reproduction/repro_kit/README_実行手順.md`.
- `evidence/` – 140-classification correspondence (`classification_evidence_140.csv`, `origin_correspondence.csv`),
  evidence manifest, originals collection hash list, hand-over forms.
- `manifests/` – publication-only SHA-256 manifest (`SHA256SUMS_publication.txt`) and the exclusion note.

## Scope statements
- 140 are **classification comparisons**, not 140 trajectories. G2 status: 69 MATCH / 71 PARTIAL / 0 MISMATCH. G4: HOLD.
- Independent third-party execution: **not yet performed**. Technical collation results are not a formal verification status.
- Bit-wise agreement is claimed only in the confirmed environment (Python 3.13 / NumPy 2.5 / SciPy 1.18).
- The Layer I 300-trial data remain in the existing `data/` directory of this repository, unchanged.

## Not published here
Internal packages, approval/authorization records (see `manifests/EXCLUDED_NOTE.md`), keys or secrets,
non-public theory materials, and the paper manuscript.
`SOURCE_PACKAGE_README.md` is the original package README (redacted derivative).

## Integrity
`sha256sum -c manifests/SHA256SUMS_publication.txt` from this directory's parent-relative root
(run inside `validation/mfd_reproduction_rev3/`). Note: `reproduction/repro_kit/KIT_MANIFEST_sha256.txt`,
`expected_evidence_sha256.txt` and `evidence_input/SHA256SUMS.txt` still list five authorization-related
evidence files that are deliberately not published; the kit's own evidence-hash step will therefore report
those five as absent. This is expected.
