# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Load/stress diagnostics computed from simulation output (read-only diagnostic layer).

Implementation version: adds an adapter (_STATE2STATUS) mapping simulate_dg's state names
(NATIVE/MIRROR_TRAP/KINETIC_TRAP/FOLDING) to the status vocabulary (natural/mirror/local/
unfinished) used by the theory-form definitions in mfd_stress_theory.py.
"""
import numpy as np

def compute_effective_flux(U0_array, t_fold_array):
    U0_array = np.asarray(U0_array); t_fold_array = np.asarray(t_fold_array)
    return U0_array / t_fold_array

def compute_instant_flux(delta_U_array, dt):
    return -np.asarray(delta_U_array) / dt

def compute_stress_instant(J_in_array, D_max):
    return np.asarray(J_in_array) / D_max

def compute_overload_time(S_array, dt, S_threshold=1.0):
    """
    注意：DiBaS は J_in を D_max 以下に射影で強制するため、S(t) は構造的にほぼ 1 を超えない。
    S_threshold=1.0 のままだと「容量超過時間」ではなく「Newton許容誤差による丸め越え」しか
    拾わない（本文参照）。容量に張り付いていた時間を見たい場合は S_threshold=1 - eps を使う。
    """
    S_array = np.asarray(S_array)
    return np.sum(S_array > S_threshold) * dt

_STATE2STATUS = {"NATIVE": "natural", "MIRROR_TRAP": "mirror",
                 "KINETIC_TRAP": "local", "FOLDING": "unfinished"}

def _status(results):
    """results の要素が {'status': ...} でも simulate_dg 由来の {'state': ...} でも受け付ける"""
    out = []
    for r in results:
        if "status" in r:
            out.append(r["status"])
        elif "state" in r:
            out.append(_STATE2STATUS.get(r["state"], "unfinished"))
        else:
            raise KeyError("result に 'status' も 'state' もありません")
    return out

def compute_unfinished_ratio(results):
    statuses = _status(results); total = len(statuses)
    return sum(1 for s in statuses if s == "unfinished") / total if total > 0 else np.nan

def compute_misfold_ratio(results):
    statuses = _status(results); total = len(statuses)
    return sum(1 for s in statuses if s in ("mirror", "local")) / total if total > 0 else np.nan
