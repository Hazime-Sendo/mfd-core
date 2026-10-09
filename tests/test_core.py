# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""Fast checks (< 1 min): `pytest -q` from the repository root."""
import json
import os
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from mfd_discrete_gradient import CapMob, CirMob, GoLandscape, dg_step, make_native, simulate_dg  # noqa: E402


def test_discrete_gradient_is_monotone_for_any_step_and_circulation():
    n = 12
    x_nat = make_native(n, 0)
    land = GoLandscape(x_nat)
    rng = np.random.default_rng(0)
    for a in (0.0, 4.0, 64.0):
        cap, cir = CapMob(n), CirMob(n, a)
        M3 = np.kron(np.diag(cap.g) + cir.matrix(cap.g), np.eye(3))
        x = x_nat + 0.3 * rng.normal(size=(n, 3))
        Ux = land.energy_grad(x)[0]
        for h in (1e-3, 1e-2, 1e-1):
            for _ in range(20):
                out = dg_step(land, M3, x, Ux, h)
                assert out is not None
                assert out[1] <= Ux + 1e-9
                x, Ux = out


def test_short_simulation_is_deterministic_and_monotone():
    r1 = simulate_dg(n=10, T_phys=2.0, dt=5e-3, d_max=500.0, a=4.0, seed=3)
    r2 = simulate_dg(n=10, T_phys=2.0, dt=5e-3, d_max=500.0, a=4.0, seed=3)
    assert np.array_equal(r1["U"], r2["U"])
    assert np.diff(r1["U"]).max() <= 0.0


def test_committed_sweep_reproduces_headline_numbers():
    runs = [json.loads(l) for l in open(os.path.join(ROOT, "data", "dmax_sweep_runs.jsonl"))]
    assert len(runs) == 300
    assert abs(np.mean([r["U0"] for r in runs]) - 6716.8) < 0.05
    cnt = {}
    for r in runs:
        cnt[r["state"]] = cnt.get(r["state"], 0) + 1
    assert (cnt["NATIVE"], cnt["MIRROR_TRAP"], cnt["KINETIC_TRAP"], cnt["FOLDING"]) == (159, 125, 15, 1)
    assert max(r["dU_max"] for r in runs) < 0.0
