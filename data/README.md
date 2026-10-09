# data/

- `dmax_sweep_runs.jsonl` - raw per-trial output of the main 300-trial study (one JSON object
  per line): `a` (circulation strength), `D_max` (dissipation cap), `seed` (0-9, initial
  condition), `state` (`NATIVE` | `MIRROR_TRAP` | `KINETIC_TRAP`, or `FOLDING` = unfinished: no terminal state within the step budget),
  `t` (physical relaxation time), `U0` (initial energy), `clip_time` (time spent at the cap),
  `dU_max` (largest single-step energy change over the whole (a, D_max) cell, always negative, i.e. monotone; this cell-level field is not written by the regeneration script). Produced by
  `scripts/05_dmax_sweep_300trials.py`; `SHA256SUMS` holds its checksum.
- `fig2_data_reference.json` - reference grid for Fig. 2 (monotone = 1, otherwise 0), identical to
  what `scripts/01_splitting_vs_discrete_gradient.py` regenerates.
