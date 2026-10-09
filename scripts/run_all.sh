#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
# Usage:  bash scripts/run_all.sh [quick|full]
#   quick (default, a few minutes): everything except the slow re-runs; Tables 1-2 are
#          recomputed from the committed data.
#   full  (about 1-2 h on one core): additionally re-runs the 300-trial sweep from scratch and
#          compares it trial-by-trial with data/dmax_sweep_runs.jsonl, plus the step-size and
#          threshold-sensitivity studies.
# Logs go to results/logs/, figures to results/figures/.
set -euo pipefail
cd "$(dirname "$0")/.."
MODE="${1:-quick}"
mkdir -p results/logs results/figures
run() { local n="$1"; shift; echo ">>> $n $*"; python3 "scripts/$n.py" "$@" 2>&1 | tee "results/logs/$n.log"; }

run 01_splitting_vs_discrete_gradient
run 02_convergence_smooth_and_gomodel
run 03_convergence_long_time_branching
run 04_self_convergence_richardson
run 08_circulation_pilot
run 10_reflection_equivariance
if [ "$MODE" = "full" ]; then
  run 05_dmax_sweep_300trials
  run 06_step_size_robustness
  run 07_threshold_sensitivity
else
  run 05_dmax_sweep_300trials --tables-only
fi
run 09_make_figures
python3 -m pytest -q tests 2>&1 | tee results/logs/pytest.log || true
echo "done ($MODE)"
