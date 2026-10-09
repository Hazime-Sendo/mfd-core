# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces Section 5.5 / ../docs/sensitivity_analysis.md: re-runs the
(a=0, D_max=200) and (a=4, D_max=500) cells (seeds 0-9) while varying each
of the five FoldDiag terminal-state classification thresholds away from its
baseline value, and reports whether the classification of any trial changes.

Baseline: eps_U=1e-4, sat_frac=0.8, hold=5, q_fold=0.9, rmsd_fold=0.5,
noise_k=0.3 (as used throughout the main 300-trial dataset).

Expected finding: hold, sat_frac and noise_k have no effect on any
classification in either cell; the RMSD cutoff (and, at a=0 only, the
plateau-energy tolerance eps_U) shift a small number of borderline
mirror/local-trap classifications but do not change the native count
materially.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from mfd_discrete_gradient import simulate_dg

CONDITIONS = [
    dict(a=0.0, D_max=200.0),
    dict(a=4.0, D_max=500.0),
]

VARIANTS = {
    'hold=3': dict(hold=3),
    'hold=10': dict(hold=10),
    'sat_frac=0.6': dict(sat_frac=0.6),
    'sat_frac=0.9': dict(sat_frac=0.9),
    'noise_k=0.15': dict(noise_k=0.15),
    'noise_k=0.5': dict(noise_k=0.5),
    'q_fold=0.8': dict(q_fold=0.8),
    'q_fold=0.95': dict(q_fold=0.95),
    'rmsd_fold=0.3': dict(rmsd_fold=0.3),
    'rmsd_fold=0.7': dict(rmsd_fold=0.7),
    'eps_U=1e-3': dict(eps_U=1e-3),
    'eps_U=1e-5': dict(eps_U=1e-5),
}

LABEL = {'NATIVE': 'N', 'MIRROR_TRAP': 'M', 'KINETIC_TRAP': 'L'}
SEEDS = range(10)


def classify(a, D_max, kwargs):
    out = []
    for seed in SEEDS:
        r = simulate_dg(n=20, dt=5e-3, d_max=D_max, a=a, seed=seed,
                         native_seed=0, max_steps=20000, **kwargs)
        out.append(LABEL.get(r['state'], 'U'))
    return out


if __name__ == "__main__":
    for cond in CONDITIONS:
        a, d = cond['a'], cond['D_max']
        print(f"=== a={a}, D_max={d} (seeds 0-9) ===")
        baseline = classify(a, d, {})
        print(f"  {'baseline':<14}: {' '.join(baseline)}")
        for name, kw in VARIANTS.items():
            cls = classify(a, d, kw)
            n_diff = sum(c != b for c, b in zip(cls, baseline))
            flag = f"  <- {n_diff} differ from baseline" if n_diff else ""
            print(f"  {name:<14}: {' '.join(cls)}{flag}")
        print()
