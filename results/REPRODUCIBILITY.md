# Reproducibility log

Environment: see `environment.txt` (Python 3.11.15, NumPy 2.4.4, SciPy 1.17.1, Matplotlib 3.10.9,
pytest 9.1.1; Linux, single process, CPU only). Run date: 2026-10-09. Raw logs: `logs/`.

| Check | Command | Result |
|---|---|---|
| Fig. 2 grid | `01_splitting_vs_discrete_gradient.py` | split 65/112 monotone, plain-Newton dg 80/112 (all 32 failures are Newton non-convergence, U never increases), dg with step bisection 112/112; `results/fig2_data.json` identical to `data/fig2_data_reference.json` |
| §3.3 order (smooth problem) | `02_convergence_smooth_and_gomodel.py` | p = 2.00 ± 0.02 over 9 step halvings (2.012 … 2.017) |
| §3.3 long-time branching | `03_convergence_long_time_branching.py` | ran, exit 0 (branching reported as in the paper) |
| §3.3 self-convergence | `04_self_convergence_richardson.py` | ran, exit 0 (see log and `docs/convergence_verification.md`)
| 300-trial sweep (full re-run, 08:19–09:25 UTC) | `05_dmax_sweep_300trials.py` | `REPRODUCTION CHECK: 300 regenerated vs 300 committed trials; state mismatches=0, numeric mismatches=0, missing=0 -> IDENTICAL` |
| Table 1 | `05 … --tables-only` | τ(a) = 34.46±2.69, 13.17±1.04, 4.26±0.52, 2.99±0.12, 3.74±0.06 for a = 0,1,4,8,16 |
| Table 2 | `05 … --tables-only` | native counts 40/33/35/25/26 of 60 per a; exact (Clopper–Pearson) CIs; p = 0.001, 0.519, 0.148, 0.683, 0.597 |
| §5.5 step size | `06_step_size_robustness.py` | a=16: 2/10 and 3/10 trials reclassified, mean-time change 5.7 % / 6.1 %; a=0: 0/10 at dt/2 (1.3 %) |
| §5.5 thresholds | `07_threshold_sensitivity.py` | rmsd_fold=0.3 changes 3/10 (a=0,D_max=200) and 2/10 (a=4,D_max=500) trials; other variants ≤2/10 |
| §6.3 pilot | `08_circulation_pilot.py` | ran, exit 0 |
| Figures 1–5 | `09_make_figures.py` | regenerated to `results/figures/` (PDF + PNG) |
| Unit tests | `pytest -q tests` | 3 passed |

Notes: scripts 05–07 ran concurrently on one machine; results do not depend on scheduling because
all randomness is seeded. Table 2 interval labelling and the §5.5 a=16 numbers were corrected in the
manuscript after an independent review (`docs/manuscript_corrections.md`).

Addendum (2026-10-09): `05 --tables-only` additionally prints Table 2b (seed-level sign test: a=0 8:2, p=0.109; a=1 5:4; a=4 7:3; a=8 4:5; a=16 4:4). The same ten seeds are shared by all D_max cells, so the pooled Table 2 p-values assume independence that does not hold.

Addendum 2: `10_reflection_equivariance.py` (a = 0, 4, 16; seeds 0-9; D_max = 500): reflecting the initial chain x -> (-x, y, z) swaps NATIVE and MIRROR_TRAP (KINETIC_TRAP stays) with identical relaxation time, identical U history and identical final coordinates (up to the reflection) in 30/30 runs (max differences exactly 0).
