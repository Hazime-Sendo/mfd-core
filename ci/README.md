# CI verification (MFD-CI-001)

Automated re-verification of the published, stored assets of this repository. It never generates a new trial or trajectory and does not touch non-public assets.

- Trigger: manual only (`workflow_dispatch`). Permissions: `contents: read`. No secrets.
- Runner: GitHub-hosted `ubuntu-24.04`. CI-02 uses Python 3.11 with `requirements-lock.txt`; CI-01/03/04/05 use Python 3.13 with `ci/requirements-kit-ci.txt` (the kit's confirmed environment). Actions are pinned by commit SHA.

| ID | Check | Notes |
|---|---|---|
| CI-01 | Public asset integrity | `PUBLIC_MANIFEST_SHA256.txt` (190 entries), kit verifier (237 entries), 15 verifier tests; detects missing, altered and unregistered files |
| CI-02 | Regression tests | `pytest tests/`; exit code and counts recorded |
| CI-03 | Layer I | stored 300 trials re-aggregated; no new trial |
| CI-04 | Layer II | 21 trajectories with data; 12 ledger-only are never judged "reproduced" (result: PARTIAL by design) |
| CI-05 | Layer III | 140 stored comparisons, existing code |
| CI-06 | REVTeX independent build | HELD (BLOCKED, not run) until the publisher's conditions are confirmed; not a pass |

Verdicts: PASS / FAIL / BLOCKED / PARTIAL. Overall: FAIL > BLOCKED > PARTIAL > PASS (held CI-06 counts as PARTIAL). An unexecuted check is never PASS. The expected values live in `ci/expected.json`; any difference is FAIL.

Evidence (logs, exit codes, counts, verdicts, SHA-256 of outputs) is uploaded as Actions artifacts. These runs are producer-side automation, not a third-party replication.

CI files are registered in `ci/CI_MANIFEST_SHA256.txt` so that the public manifest scope stays unchanged.
