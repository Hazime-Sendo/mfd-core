# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces Section 5.5 ("Robustness to step size"): re-runs the
(a, D_max=500) cells at half the step size (and, for a=16, a further
quarter), holding the total physical time budget T = dt * max_steps = 100
fixed, and reports how many of the 10 trials change terminal-state
classification and by how much the mean relaxation time shifts, relative
to the baseline dt=5e-3 run.

The manuscript reports: for a in {0,1,4,8}, counts identical or changed by at most one trial
and mean-time changes <= 1.4%; for a=16, 2/10 (h/2) and 3/10 (h/4) trials reclassified, with
mean relaxation times changed by 5.7% and 6.1% respectively.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from mfd_discrete_gradient import run_go_fold

A_VALUES = [0.0, 1.0, 4.0, 8.0, 16.0]
D_MAX = 500.0
TRIALS = 10
BASE_DT = 5e-3
BASE_MAX_STEPS = 20000
T_PHYS = BASE_DT * BASE_MAX_STEPS  # keep this fixed as dt shrinks

TERMINAL_KEY = {"NATIVE": "native", "MIRROR_TRAP": "mirror", "KINETIC_TRAP": "local"}


def run_cell(a, dt):
    max_steps = int(round(T_PHYS / dt))
    _, runs = run_go_fold(a=a, D_max=D_MAX, dt=dt, max_steps=max_steps,
                           trials=TRIALS, n=20, native_seed=0, return_runs=True)
    return runs


if __name__ == "__main__":
    for a in A_VALUES:
        dts = [BASE_DT, BASE_DT / 2] + ([BASE_DT / 4] if a == 16 else [])
        print(f"=== a={a}, D_max={D_MAX} ===")
        rows = {}
        for dt in dts:
            runs = run_cell(a, dt)
            states = [r['state'] for r in runs]
            times = [r['t'] for r in runs if r['state'] in TERMINAL_KEY]
            mean_t = float(np.mean(times)) if times else float('nan')
            rows[dt] = (states, mean_t)
            print(f"  dt={dt:.6f}: states={states}")
            print(f"             mean relaxation time over terminal trials = {mean_t:.3f}")
        base_dt = dts[0]
        base_states, base_t = rows[base_dt]
        for dt in dts[1:]:
            states, mean_t = rows[dt]
            n_reclassified = sum(s1 != s2 for s1, s2 in zip(base_states, states))
            pct = 100 * abs(mean_t - base_t) / base_t if base_t else float('nan')
            print(f"  dt={base_dt:.6f} -> {dt:.6f}: "
                  f"{n_reclassified}/{TRIALS} trials reclassified, "
                  f"mean relaxation time changed by {pct:.1f}%")
        print()
