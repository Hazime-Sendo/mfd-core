# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
MFD abstract stress theory (pure, implementation-independent definitions; kept verbatim as the
formal reference, with signatures unchanged):
  J_in^(eff) = U0 / t_fold (effective load flux),  J_in(t_n) = -dU_n / dt (instantaneous flux),
  S(t_n) = J_in(t_n) / D_max (instantaneous stress),  T_over = sum over {S > S_threshold} of dt,
  plus the unfinished/misfold ratios. Result objects use status in
  {'natural','mirror','local','unfinished'}; stress_metrics.py bridges to simulate_dg's schema.

(Original Japanese docstring follows.)
MFD 抽象ストレス理論（論文の理論セクション用・純粋形）
============================================================
このファイルは実装に依存しない定義のみを与える。
  - J_in^(eff) = U0 / t_fold                       （有効負荷フラックス）
  - J_in(t_n)  = -ΔU_n / dt                         （瞬間負荷フラックス）
  - S(t_n)     = J_in(t_n) / D_max                  （瞬間ストレス）
  - T_over     = Σ_{S(t_n) > S_threshold} dt        （過負荷時間）
  - p_unfin, p_mis                                  （終端状態の比率）

結果オブジェクトの形（status: 'natural'/'mirror'/'local'/'unfinished'）は
理論上の分類そのものであり、特定シミュレータの出力スキーマ（state:
NATIVE/MIRROR_TRAP/...）には依存しない。Go 模型など具体的な実装への
橋渡しは stress_metrics.py（実装版）が担う。数式・シグネチャはここでは
一切変更しない。
============================================================
"""
import numpy as np

def compute_effective_flux(U0_array, t_fold_array):
    """
    有効負荷フラックス J_in^(eff) = U0 / t_fold を計算する。
    U0_array: 初期エネルギーの配列（shape: [trials]）
    t_fold_array: 到達時間（完了試行のみ）の配列（shape: [trials]）
    戻り値: J_in_eff_array（shape: [trials]）
    """
    U0_array = np.asarray(U0_array)
    t_fold_array = np.asarray(t_fold_array)

    # ゼロ割り防止：未完了試行は事前に除外しておく前提
    return U0_array / t_fold_array


def compute_instant_flux(delta_U_array, dt):
    """
    各ステップでの瞬間負荷フラックス J_in(t_n) = -ΔU_n / dt を計算する。
    delta_U_array: 各ステップのエネルギー変化 ΔU_n の配列（shape: [steps]）
    dt: タイムステップ幅
    戻り値: J_in_array（shape: [steps]）
    """
    delta_U_array = np.asarray(delta_U_array)
    return -delta_U_array / dt


def compute_stress_instant(J_in_array, D_max):
    """
    瞬間ストレス S(t_n) = J_in(t_n) / D_max を計算する。
    J_in_array: 瞬間フラックスの配列（shape: [steps]）
    D_max: 散逸容量
    戻り値: S_array（shape: [steps]）
    """
    J_in_array = np.asarray(J_in_array)
    return J_in_array / D_max


def compute_overload_time(S_array, dt, S_threshold=1.0):
    """
    過負荷時間 T_over = Σ_{S(t_n) > S_threshold} dt を計算する。
    S_array: ストレス指標 S(t_n) の配列（shape: [steps]）
    dt: タイムステップ幅
    S_threshold: 容量超過とみなす閾値（デフォルト 1.0）
    戻り値: T_over（スカラー）
    """
    S_array = np.asarray(S_array)
    mask_over = S_array > S_threshold
    return np.sum(mask_over) * dt


def compute_unfinished_ratio(results):
    """
    未完了率 p_unfin を計算する。
    results: 各試行の結果をまとめたリストや配列。
             例：{'status': 'natural'/'mirror'/'local'/'unfinished', ...} のリスト
    戻り値: p_unfin（スカラー）
    """
    statuses = [r["status"] for r in results]
    total = len(statuses)
    unfin = sum(1 for s in statuses if s == "unfinished")
    return unfin / total if total > 0 else np.nan


def compute_misfold_ratio(results):
    """
    misfolding率 p_mis = (mirror + local) / total を計算する。
    results: 各試行の結果をまとめたリストや配列。
             例：{'status': 'natural'/'mirror'/'local'/'unfinished', ...} のリスト
    戻り値: p_mis（スカラー）
    """
    statuses = [r["status"] for r in results]
    total = len(statuses)
    mis = sum(1 for s in statuses if s in ("mirror", "local"))
    return mis / total if total > 0 else np.nan
