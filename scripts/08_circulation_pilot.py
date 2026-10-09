# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces the stochastic circulation pilot measurement of Section 6.3:
a non-zero stationary signed circulation (area-sweep rate in an
internal-coordinate plane) near x^nat when a != 0, versus ~0 at a=0,
in a Langevin (T>0) extension of the deterministic dynamics -- the
expected signature of broken detailed balance from the antisymmetric
mobility A.

Note (stated explicitly in the manuscript, Limitations): this is a small,
illustrative measurement (four realizations per condition), separate from
and not part of the main 300-trial deterministic (T=0) dataset of
Section 5. It is not intended as a statistically powered result.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from metriplectic_folding import measure_circulation

N_REALIZATIONS = 4

if __name__ == "__main__":
    for a in [0.0, 1.0]:
        vals = np.array([measure_circulation(a=a, T=0.05, seed=s)
                          for s in range(N_REALIZATIONS)])
        mean = vals.mean()
        sem = vals.std(ddof=1) / np.sqrt(len(vals))
        print(f"a={a}: circulation = {mean:.3f} +/- {sem:.3f} "
              f"(n={len(vals)} realizations: {np.round(vals, 3)})")
