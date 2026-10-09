# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Reproduces the main 300-trial dataset of the manuscript (Section 5,
"Numerical results") and Tables 1-2, from which Figures 3-5 are built.

Grid: a in {0, 1, 4, 8, 16}, D_max in {200, 300, 400, 500, 700, 1000},
10 independent random initial conditions per (a, D_max) cell, dt = 5e-3,
up to 20000 steps, n = 20, native_seed = 0.

This is fully deterministic (NumPy default_rng with explicit per-trial
seeds), so running this script reproduces ../data/dmax_sweep_runs.jsonl
exactly, trial for trial -- that file is the committed output of exactly
this script and is provided so Tables 1-2 can be checked without re-running
the ~15-20 minute sweep.

Usage:
    python 05_dmax_sweep_300trials.py            # regenerate + report tables
    python 05_dmax_sweep_300trials.py --tables-only   # just recompute Tables
                                                        1-2 from the committed
                                                        data/dmax_sweep_runs.jsonl
"""
import sys
import os
import json
import math
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from mfd_discrete_gradient import run_go_fold

A_VALUES = [0.0, 1.0, 4.0, 8.0, 16.0]
DMAX_VALUES = [200.0, 300.0, 400.0, 500.0, 700.0, 1000.0]
TRIALS = 10
DT = 5e-3
MAX_STEPS = 20000
N = 20
NATIVE_SEED = 0

TERMINAL_KEY = {"NATIVE": "native", "MIRROR_TRAP": "mirror", "KINETIC_TRAP": "local"}


def run_all():
    runs = []
    for a in A_VALUES:
        for d in DMAX_VALUES:
            _, rr = run_go_fold(a=a, D_max=d, dt=DT, max_steps=MAX_STEPS,
                                 trials=TRIALS, n=N, native_seed=NATIVE_SEED,
                                 return_runs=True)
            for r in rr:
                runs.append(dict(a=a, D_max=d, **r))
    return runs


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def wilson_ci(k, n, z=1.959963984540054):
    """Wilson score interval. NOTE: Table 2 of the manuscript is captioned
    '95% Wilson interval' but its printed bounds are actually the exact
    (Clopper-Pearson) binomial interval -- see clopper_pearson_ci() below,
    which is what this script uses for the printed table. This function is
    kept for comparison; the two methods agree closely but not exactly
    (Wilson is slightly narrower)."""
    if n == 0:
        return (float('nan'), float('nan'))
    phat = k / n
    denom = 1 + z ** 2 / n
    centre = phat + z ** 2 / (2 * n)
    adj = z * math.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2))
    return ((centre - adj) / denom, (centre + adj) / denom)


def clopper_pearson_ci(k, n, alpha=0.05):
    """Exact (Clopper-Pearson) binomial confidence interval -- reproduces
    the bounds actually printed in Table 2 of the manuscript (its caption's
    label 'Wilson interval' is a documentation error; see README)."""
    from scipy.stats import beta
    lo = beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (float(lo), float(hi))


def binom_pvalue(k, n, p0=0.5):
    try:
        from scipy.stats import binomtest
        return binomtest(k, n, p0).pvalue
    except ImportError:
        from scipy.stats import binom_test
        return binom_test(k, n, p0)


def table1_decomposition(runs):
    """Regress mean relaxation time t against 1/D_max for each a; reproduces Table 1."""
    by_a = defaultdict(lambda: defaultdict(list))
    for r in runs:
        if r['state'] in ('NATIVE', 'MIRROR_TRAP', 'KINETIC_TRAP'):
            by_a[r['a']][r['D_max']].append(r['t'])
    U0_mean = float(np.mean([r['U0'] for r in runs]))
    U0_sem = float(np.std([r['U0'] for r in runs], ddof=1) / math.sqrt(len(runs)))
    print(f"Mean initial energy U0 = {U0_mean:.1f} +/- {U0_sem:.1f} (mean +/- SEM, n={len(runs)})\n")
    print("Table 1: regression estimates of tau(a) and the fitted slope")
    print(f"{'a':>4} {'tau(a)':>18} {'fitted slope':>18} {'D*=U0/tau(a)':>14}")
    for a in A_VALUES:
        xs, ys = [], []
        for d in DMAX_VALUES:
            ts = by_a[a][d]
            if ts:
                xs.append(1.0 / d)
                ys.append(float(np.mean(ts)))
        xs, ys = np.array(xs), np.array(ys)
        Amat = np.vstack([xs, np.ones_like(xs)]).T
        (slope, tau), *_ = np.linalg.lstsq(Amat, ys, rcond=None)
        resid = ys - Amat @ np.array([slope, tau])
        dof = max(len(ys) - 2, 1)
        sigma2 = float(np.sum(resid ** 2) / dof)
        cov = sigma2 * np.linalg.inv(Amat.T @ Amat)
        se_slope, se_tau = math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1])
        dstar = U0_mean / tau if tau > 0 else float('nan')
        print(f"{a:>4} {tau:>8.2f} +/- {se_tau:<6.2f} {slope:>8.0f} +/- {se_slope:<6.0f} {dstar:>8.0f}")
    print()


def table2_terminal_stats(runs):
    """Terminal-state counts and native:mirror binomial test per a; reproduces Table 2."""
    by_a = defaultdict(lambda: dict(native=0, mirror=0, local=0, unfinished=0))
    for r in runs:
        key = TERMINAL_KEY.get(r['state'], 'unfinished')
        by_a[r['a']][key] += 1
    print("Table 2: terminal-state counts per circulation strength a (60 trials/row)")
    print("(95% CI = exact/Clopper-Pearson, matching the bounds printed in the")
    print(" manuscript's Table 2 -- its caption's label 'Wilson interval' is a")
    print(" documentation error, corrected; see docs/manuscript_corrections.md)")
    print(f"{'a':>4} {'nat':>4} {'mir':>4} {'loc':>4} {'unf':>4} {'p_nat':>7} {'95% CI':>18} {'p-value':>8}")
    totals = defaultdict(int)
    for a in A_VALUES:
        c = by_a[a]
        n_nm = c['native'] + c['mirror']
        phat = c['native'] / n_nm if n_nm else float('nan')
        lo, hi = clopper_pearson_ci(c['native'], n_nm)
        p = binom_pvalue(c['native'], n_nm) if n_nm else float('nan')
        print(f"{a:>4} {c['native']:>4} {c['mirror']:>4} {c['local']:>4} {c['unfinished']:>4} "
              f"{phat:>7.3f} ({lo:.3f},{hi:.3f})   {p:>8.3f}")
        for k, v in c.items():
            totals[k] += v
    print(f"{'all':>4} {totals['native']:>4} {totals['mirror']:>4} "
          f"{totals['local']:>4} {totals['unfinished']:>4}")
    print()


def table2b_seed_level(runs):
    """Seed-level native:mirror test. The SAME ten seeds (initial conditions) are used in every
    D_max cell, so the 60 trials per a are NOT independent. For each seed, the outcome is
    'native' if native outcomes outnumber mirror outcomes over the six D_max values, 'mirror' if
    the reverse, 'tie' otherwise; an exact two-sided sign test is then applied to the seed counts."""
    by = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in runs:
        if r['state'] == 'NATIVE':
            by[r['a']][r['seed']][0] += 1
        elif r['state'] == 'MIRROR_TRAP':
            by[r['a']][r['seed']][1] += 1
    print("Table 2b: seed-level (non-pooled) native:mirror sign test, 10 seeds per a")
    print(f"{'a':>4} {'native':>7} {'mirror':>7} {'tie':>4} {'p-value':>8}")
    for a in A_VALUES:
        nn = sum(1 for v in by[a].values() if v[0] > v[1])
        mm = sum(1 for v in by[a].values() if v[1] > v[0])
        tie = len(by[a]) - nn - mm
        p = binom_pvalue(nn, nn + mm) if nn + mm else float('nan')
        print(f"{a:>4} {nn:>7} {mm:>7} {tie:>4} {p:>8.3f}")
    print()


def compare_with_committed(new, ref, rtol=1e-9):
    """Trial-by-trial comparison of a regenerated sweep against data/dmax_sweep_runs.jsonl."""
    key = lambda r: (r['a'], r['D_max'], r['seed'])
    ref_by = {key(r): r for r in ref}
    n_state = n_num = n_missing = 0
    for r in new:
        q = ref_by.get(key(r))
        if q is None:
            n_missing += 1
            continue
        if r['state'] != q['state']:
            n_state += 1
        if any(abs(r[f] - q[f]) > rtol * max(1.0, abs(q[f])) for f in ('t', 'U0', 'clip_time')):
            n_num += 1
    ok = (n_state == 0 and n_num == 0 and n_missing == 0 and len(new) == len(ref))
    print(f"REPRODUCTION CHECK: {len(new)} regenerated vs {len(ref)} committed trials; "
          f"state mismatches={n_state}, numeric mismatches={n_num}, missing={n_missing} "
          f"-> {'IDENTICAL' if ok else 'DIFFERENT'}\n")
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--tables-only', action='store_true',
                         help="skip the ~15-20 min sweep; recompute Tables 1-2 "
                              "from the committed data/dmax_sweep_runs.jsonl")
    args = parser.parse_args()

    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dmax_sweep_runs.jsonl')
    if args.tables_only:
        runs = load_jsonl(data_path)
        print(f"loaded {len(runs)} trials from {data_path}\n")
    else:
        runs = run_all()
        out_path = os.path.join(os.path.dirname(__file__), '..', 'results',
                                 'dmax_sweep_runs_regenerated.jsonl')
        with open(out_path, 'w') as f:
            for r in runs:
                f.write(json.dumps(r) + '\n')
        print(f"ran {len(runs)} trials, wrote {out_path}")
        compare_with_committed(runs, load_jsonl(data_path))

    table1_decomposition(runs)
    table2_terminal_stats(runs)
    table2b_seed_level(runs)
