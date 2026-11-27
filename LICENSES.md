# Licensing of this repository

Rights holder / attribution: **Hazime Sendo** (ORCID 0009-0007-3285-0308).

| Material | License | Where |
|---|---|---|
| Source code and scripts (Python, shell), including the code inside the reproduction kit | **Apache License 2.0** (`LICENSE`) | `src/`, `scripts/`, `tests/`, and all `*.py` / `*.sh` files under `validation/mfd_independent_reproduction_ready_kit_rev4/` |
| Data and results (raw trial records, trajectory containers `.m2` / `.npz`, ledgers, classification tables, expected values, produced outputs, logs, figures) | **Creative Commons Attribution 4.0 International (CC BY 4.0)** (`LICENSE-CC-BY-4.0.txt`) | `data/`, `results/`, and all data, `.json`, `.jsonl`, `.csv`, `.txt` output/log files under the reproduction kit |
| Technical documentation (README files, `docs/`, specifications, reports) | **CC BY 4.0** (`LICENSE-CC-BY-4.0.txt`) | `README.md`, `data/README.md`, `docs/`, `validation/…/README*.md`, `validation/…/*.md` |
| CI verification files (workflow definition, driver, expected values, requirement pins, CI documentation and CI manifest) | **Apache License 2.0** (`LICENSE`) | `ci/` and `.github/workflows/` (all files in these directories) |
| Manuscript | **Not part of this repository.** A CC BY-SA 4.0 license is planned only after the publisher's conditions have been confirmed; no manuscript license is granted here. | — |
| Non-public assets | **No public license is granted.** They are not included in this repository. | — |

Third-party libraries and GitHub Actions used by the CI remain under their own original licenses; they are not relicensed by this repository.

If a file's type is ambiguous, the table above is decisive: executable source is Apache-2.0; data and documents are CC BY 4.0.
When reusing data or documents, please attribute: "Hazime Sendo, MFD-core (https://github.com/Hazime-Sendo/mfd-core), CC BY 4.0".
