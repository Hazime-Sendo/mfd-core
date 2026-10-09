# MFD-core: verification code

Reproduction code, raw data and scripts for

> H. Sendo, "A Metriplectic Discrete-Gradient Model of Dissipation-Capped Relaxation:
> Monotone Integration, a Two-Regime Time Decomposition, and a Circulation-Induced
> Crossover," submitted to *Journal of Statistical Physics* (2026).

Everything here is produced by deterministic, seeded numerical simulation (no physical
experimental data). Every table, figure and quantitative claim of the paper can be regenerated.

## Folder map

```
src/        core model and integrator
data/       committed raw output of the 300-trial sweep + Fig. 2 reference data (+ SHA256SUMS)
scripts/    one script per claim/table/figure, plus run_all.sh
results/    outputs written by the scripts (figures/, logs/, REPRODUCIBILITY.md, environment.txt)
tests/      unit tests (pytest)
docs/       convergence write-up, sensitivity analysis, manuscript corrections
```

| `src/` file | Contents |
|---|---|
| `metriplectic_folding.py` | `GoLandscape`, `CapMob` (self-evolving G), `CirMob` (A = a√G J √G), `FoldDiag` (read-only terminal-state classifier), Langevin integrator used only in the §6.3 pilot |
| `mfd_discrete_gradient.py` | Gonzalez discrete-gradient step `dg_step`, `simulate_dg` (with DiBaS cap), `run_go_fold` (batch trials) |
| `stress_metrics.py`, `mfd_stress_theory.py` | Diagnostic/stress metrics (adapter form and implementation-independent reference form) |

| Script | Paper item | Runtime |
|---|---|---|
| `01_splitting_vs_discrete_gradient.py` | §3.2, Fig. 2 (writes `results/fig2_data.json`) | seconds |
| `02_convergence_smooth_and_gomodel.py` | §3.3, p = 2.00 ± 0.02 | seconds–minutes |
| `03_convergence_long_time_branching.py` | §3.3, discrete attractor branching | minutes |
| `04_self_convergence_richardson.py` | §3.3, self-convergence | minutes |
| `05_dmax_sweep_300trials.py` | §5, Tables 1–2 (`--tables-only` recomputes from committed data) | seconds / ≈1 h full |
| `06_step_size_robustness.py` | §5.5 step-size robustness | tens of minutes |
| `07_threshold_sensitivity.py` | §5.5 classifier-threshold sensitivity | tens of minutes |
| `08_circulation_pilot.py` | §6.3 Langevin circulation pilot | minutes |
| `10_reflection_equivariance.py` | Label discussion: reflecting the initial chain swaps NATIVE/MIRROR_TRAP exactly (30/30 runs, a = 0, 4, 16) | ≈1 min |
| `09_make_figures.py` | Figs. 1–5 (PDF + PNG into `results/figures/`) | seconds |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # or requirements-lock.txt for the exact tested versions
bash scripts/run_all.sh quick               # tables from committed data, figures, short checks
bash scripts/run_all.sh full                # additionally re-runs sweep, 06 and 07 from scratch
python3 -m pytest -q tests                  # unit tests
```

Run each script from the repository root (`python3 scripts/05_dmax_sweep_300trials.py --tables-only`).
Logs are written to `results/logs/`.

### Verifying the main dataset

`python3 scripts/05_dmax_sweep_300trials.py` re-runs all 300 trials (a ∈ {0,1,4,8,16} ×
D_max ∈ {200,300,400,500,700,1000} × 10 seeds), writes
`results/dmax_sweep_runs_regenerated.jsonl` and compares it trial by trial with
`data/dmax_sweep_runs.jsonl`; it prints `REPRODUCTION CHECK … IDENTICAL` on success.
`sha256sum -c data/SHA256SUMS` checks the committed data files.

## Determinism and environment

All randomness uses explicit integer seeds (`numpy.random.default_rng`). Results were produced
with Python 3.11, NumPy 2.4, SciPy 1.17, Matplotlib 3.10 (see `results/environment.txt`).
Floating-point results can differ in the last digits across BLAS/CPU builds; comparisons use a
relative tolerance (1e-9) and terminal-state labels. See `results/REPRODUCIBILITY.md` for the
log of runs made for this release.

## Manuscript corrections

An independent re-run of the scripts found two claims in an earlier manuscript draft that did
not match the code (Table 2 interval label: exact Clopper–Pearson, not Wilson; §5.5 a = 16
step-size sensitivity: 2/10 and 3/10 trials reclassified, 5.7 %/6.1 % mean-time change). Both are
corrected in the manuscript; details in `docs/manuscript_corrections.md`.

## Caveats

- The same ten seeds are used in every D_max cell, so the 60 trials per a are not independent; `05 --tables-only` prints a seed-level test (Table 2b) next to the pooled one.
- Fig. 2(b): failures of the plain unified step are Newton non-convergence; with step bisection all 112 cells are monotone (`results/fig2_data.json`, key `dg_bisect`).

## Citation and release

See `CITATION.cff` / `.zenodo.json`. A Zenodo DOI will be minted from a tagged GitHub release and
added here (TODO: insert DOI after release).

## License

Code, data and scripts: Apache License 2.0 (`LICENSE`). The manuscript is distributed separately
under CC BY-SA 4.0 and is not part of this repository.
