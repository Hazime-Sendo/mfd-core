# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""
Regenerates all manuscript figures (Figs. 1-5) from the committed data, as vector PDF (for
submission) and PNG (for preview), into results/figures/.

  Fig. 1  model architecture (schematic, drawn here)
  Fig. 2  monotonicity region, operator splitting vs discrete gradient   <- Fig. 2 grid data
  Fig. 3  mean relaxation time vs D_max, log-log, with t = U0/D_max + tau(a)   <- data/dmax_sweep_runs.jsonl
  Fig. 4  tau(a) with regression standard errors                         <- data/dmax_sweep_runs.jsonl
  Fig. 5  terminal-state composition per (a, D_max) cell                 <- data/dmax_sweep_runs.jsonl

Figure titles are intentionally omitted (captions live in the manuscript text, per the journal's
instructions). Categories are distinguished by hatching/markers as well as colour.

Fig. 2 data: results/fig2_data.json if script 01 has been run, else data/fig2_data_reference.json
(identical content).
"""
import importlib.util
import json
import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.linewidth": 0.8, "pdf.fonttype": 42, "ps.fonttype": 42,
})
MM = 1 / 25.4
C_NAT, C_MIR, C_LOC, C_UNF = "#1b9e77", "#e6ab02", "#d95f02", "#7f7f7f"   # colour-blind-safe set


def _load_sweep_module():
    spec = importlib.util.spec_from_file_location("sweep", os.path.join(HERE, "05_dmax_sweep_300trials.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sweep = _load_sweep_module()
runs = sweep.load_jsonl(os.path.join(ROOT, "data", "dmax_sweep_runs.jsonl"))
A_VALUES, DMAX_VALUES = sweep.A_VALUES, sweep.DMAX_VALUES
TERMINAL = ("NATIVE", "MIRROR_TRAP", "KINETIC_TRAP")


def save(fig, name):
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight", **kw)
    plt.close(fig)
    print("wrote", name)


def fit_tau(runs):
    """tau(a) and its standard error from t = slope/D_max + tau (same regression as Table 1)."""
    by = defaultdict(lambda: defaultdict(list))
    for r in runs:
        if r["state"] in TERMINAL:
            by[r["a"]][r["D_max"]].append(r["t"])
    out = {}
    for a in A_VALUES:
        xs = np.array([1.0 / d for d in DMAX_VALUES if by[a][d]])
        ys = np.array([np.mean(by[a][d]) for d in DMAX_VALUES if by[a][d]])
        X = np.vstack([xs, np.ones_like(xs)]).T
        (slope, tau), *_ = np.linalg.lstsq(X, ys, rcond=None)
        res = ys - X @ np.array([slope, tau])
        cov = float(np.sum(res ** 2) / max(len(ys) - 2, 1)) * np.linalg.inv(X.T @ X)
        out[a] = dict(tau=tau, se=math.sqrt(cov[1, 1]), means={d: float(np.mean(by[a][d])) for d in DMAX_VALUES if by[a][d]})
    return out


def fig1():
    fig, ax = plt.subplots(figsize=(174 * MM, 100 * MM))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")

    def box(x, y, w, h, text, fc, ec, ls="-"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5",
                                    fc=fc, ec=ec, lw=1.1, ls=ls))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)

    def arrow(p, q, style="-", color="k", txt=None, off=(0, 1.5)):
        ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="-|>", lw=1.0, ls=style, color=color))
        if txt:
            ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], txt, fontsize=7, ha="center", color=color)

    box(35, 49, 30, 9, "Potential $U(x)$\n(Go-model landscape)", "#fff2cc", "#b45f06")
    box(2, 28, 28, 12, "Symmetric mobility\n$G=\\mathrm{diag}(g)\\succ0$\n(self-evolving)", "#d9ead3", "#38761d")
    box(70, 28, 28, 12, "Antisymmetric mobility\n$A=a\\sqrt{G}\\,J\\sqrt{G}$", "#cfe2f3", "#1155cc")
    box(26, 12, 48, 11, "Discrete-gradient step for $\\dot x=-(G+A)\\nabla U$\n"
        "$U(y)-U(x)=-h\\,\\bar\\nabla U\\cdot G\\bar\\nabla U\\leq0$", "#f4cccc", "#990000")
    box(1, 0.5, 34, 7, "DiBaS cap: $s=\\min(1,D_{\\max}/D)$\n(rescales the step)", "#ead1dc", "#a64d79")
    box(65, 0.5, 34, 7, "Terminal-state diagnosis\n(read-only; no feedback)", "#eeeeee", "#666666", ls="--")
    arrow((50, 49), (50, 23.6), txt="$\\nabla U$", off=(3, 0))
    arrow((16, 28), (32, 23.6)); arrow((84, 28), (68, 23.6))
    arrow((22, 8.4), (34, 11.6))
    arrow((66, 11.6), (80, 8.4), style="--", color="#666666")
    arrow((29, 23.6), (11, 27.6), style=":", color="#38761d")
    ax.text(5, 22, "local contacts $Q_i$\nupdate $g$", fontsize=7, color="#38761d", ha="left")
    save(fig, "Fig1")


def fig2():
    p = os.path.join(ROOT, "results", "fig2_data.json")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "data", "fig2_data_reference.json")
    d = json.load(open(p))
    a_list, dt_list = d["a_list"], d["dt_list"]
    fig, axes = plt.subplots(1, 2, figsize=(174 * MM, 70 * MM), sharey=True)
    for ax, key, lab in zip(axes, ("split", "dg"), ("(a) Operator splitting", "(b) Discrete gradient, plain Newton solve")):
        Z = np.array(d[key])[:, ::-1].T            # rows: dt ascending upward
        for i in range(Z.shape[0]):
            for j in range(Z.shape[1]):
                ok = Z[i, j] > 0.5
                if ok:
                    fc, hatch = "#1b9e77", None
                elif key == "split":
                    fc, hatch = "#ffffff", "xxx"            # U increased or diverged
                else:
                    fc, hatch = "#d9d9d9", "..."            # Newton solve did not converge; U never increased
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fc=fc, ec="#444444", lw=0.3, hatch=hatch))
        ax.set_xlim(-.5, len(a_list) - .5); ax.set_ylim(-.5, len(dt_list) - .5)
        ax.set_xticks(range(len(a_list))); ax.set_xticklabels(a_list)
        ax.set_xlabel("circulation strength $a$"); ax.set_title(lab, fontsize=9)
    axes[0].set_yticks(range(len(dt_list))); axes[0].set_yticklabels(dt_list[::-1])
    axes[0].set_ylabel("step size $h$")
    fig.legend(handles=[Patch(fc="#1b9e77", ec="#444", label="monotone over 400 steps"),
                        Patch(fc="white", ec="#444", hatch="xxx", label="U increased or diverged"),
                        Patch(fc="#d9d9d9", ec="#444", hatch="...", label="Newton did not converge (U never increased)")],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.12))
    save(fig, "Fig2")


def fig3(fit):
    U0 = float(np.mean([r["U0"] for r in runs]))
    fig, ax = plt.subplots(figsize=(120 * MM, 90 * MM))
    cols = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    marks = ["o", "s", "^", "D", "v"]
    dd = np.logspace(math.log10(180), math.log10(1100), 100)
    for a, c, m in zip(A_VALUES, cols, marks):
        xs = sorted(fit[a]["means"])
        ax.plot(xs, [fit[a]["means"][d] for d in xs], m, color=c, ms=5, ls="none", label=f"$a={a:g}$")
        ax.plot(dd, U0 / dd + fit[a]["tau"], "-", color=c, lw=1.0)
    ax.plot(dd, U0 / dd, "k--", lw=0.9, label="$U_0/D_{\\max}$")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([200, 300, 500, 700, 1000]); ax.set_xticklabels(["200", "300", "500", "700", "1000"])
    ax.set_yticks([10, 20, 30, 50, 70]); ax.set_yticklabels(["10", "20", "30", "50", "70"])
    ax.minorticks_off()
    ax.set_xlabel("$D_{\\max}$"); ax.set_ylabel("mean relaxation time $t$")
    ax.legend(ncol=2, frameon=False)
    save(fig, "Fig3")


def fig4(fit):
    fig, ax = plt.subplots(figsize=(84 * MM, 70 * MM))
    ax.errorbar(A_VALUES, [fit[a]["tau"] for a in A_VALUES], yerr=[fit[a]["se"] for a in A_VALUES],
                fmt="o-", color="#1f4e9c", capsize=3, ms=4, lw=1.0)
    ax.set_xlabel("circulation strength $a$"); ax.set_ylabel("$\\tau(a)$")
    save(fig, "Fig4")


def fig5():
    cnt = defaultdict(lambda: defaultdict(int))
    for r in runs:
        k = {"NATIVE": "native", "MIRROR_TRAP": "mirror", "KINETIC_TRAP": "local trap"}.get(r["state"], "unfinished")
        cnt[(r["a"], r["D_max"])][k] += 1
    spec = [("native", C_NAT, ""), ("mirror", C_MIR, "//"), ("local trap", C_LOC, "\\\\"), ("unfinished", C_UNF, "..")]
    fig, axes = plt.subplots(1, 5, figsize=(174 * MM, 62 * MM), sharey=True)
    for ax, a in zip(axes, A_VALUES):
        bottom = np.zeros(len(DMAX_VALUES))
        for name, c, h in spec:
            v = np.array([cnt[(a, d)][name] for d in DMAX_VALUES], float)
            ax.bar(range(len(DMAX_VALUES)), v, bottom=bottom, color=c, hatch=h, ec="white", lw=0.4)
            bottom += v
        ax.set_xticks(range(len(DMAX_VALUES))); ax.set_xticklabels([str(int(d)) for d in DMAX_VALUES], rotation=90, fontsize=6.5)
        ax.set_title(f"$a={a:g}$", fontsize=9); ax.set_xlabel("$D_{\\max}$"); ax.set_ylim(0, 10)
    axes[0].set_ylabel("trials (of 10)")
    fig.legend(handles=[Patch(fc=c, hatch=h, ec="white", label=n) for n, c, h in spec],
               loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.12))
    save(fig, "Fig5")


if __name__ == "__main__":
    fit = fit_tau(runs)
    fig1(); fig2(); fig3(fit); fig4(fit); fig5()
