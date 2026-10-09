# Sensitivity of the terminal-state classification to its thresholds

`FoldDiag` classifies a trajectory using five thresholds (baseline in parentheses): plateau
tolerance `eps_U` (1e-4), plateau-noise scale `noise_k` (0.3), contact-fraction cutoff `q_fold`
(0.9), RMSD cutoff `rmsd_fold` (0.5), hold count `hold` (5), and cap-saturation fraction
`sat_frac` (0.8). `scripts/07_threshold_sensitivity.py` re-runs the cells `(a=0, D_max=200)` and
`(a=4, D_max=500)` (seeds 0-9) with each threshold varied one at a time and compares the 10
classifications with the baseline; the output is stored in `results/logs/07_threshold_sensitivity.log`.

Summary of the findings reported in the paper:
- `hold`, `sat_frac`, `noise_k` and `q_fold` do not change any of the 20 classifications.
- `rmsd_fold` (and, for `a = 0` only, `eps_U`) re-assigns a few borderline mirror / local-trap /
  unfinished trials; these thresholds matter most at `a = 0`.
- Circulating systems (`a = 4`) are markedly less sensitive to the thresholds than `a = 0`.
- Per-cell caveat: with only 10 trials, a tighter `rmsd_fold = 0.3` can change the *native* count
  of the `a = 0` cell appreciably; the aggregate native excess in Table 2 of the paper uses the
  baseline thresholds. See the log for the exact per-seed classifications.

Note on labels: `MIRROR_TRAP` is a basin label for a minimum energetically equivalent to the native state, not an energetic trap; `KINETIC_TRAP` is a threshold-dependent plateau label that may include states stalled near saddle points. See `docs/manuscript_corrections.md`.
