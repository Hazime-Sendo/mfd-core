# Corrections made to the manuscript after independent verification

An independent re-run of all eight `verification/` scripts against the
committed code, data, and `paper/mfd_manuscript.tex` surfaced two real
discrepancies between the manuscript's specific numerical claims and what
the (fully deterministic, seeded) code actually produces. Both have been
corrected in the manuscript. This file records what was found and what was
changed, in the same spirit as the native:mirror correction already
documented in Section 5.4 of the paper itself.

## 1. Table 2's caption mislabeled its confidence-interval method

**Finding.** The 95% CIs printed in Table 2 do not match a Wilson score
interval (which is what the caption said), but they match an exact
(Clopper–Pearson) binomial interval exactly, to three decimals, for all
five rows. E.g. at $a=0$ (40 native / 15 mirror): Wilson gives
$(0.598, 0.827)$; Clopper–Pearson gives $(0.590, 0.839)$, which is what
the table actually printed.

**Cause.** The original analysis almost certainly used
`scipy.stats.binomtest(...).proportion_ci()` without an explicit `method`
argument, whose default is `method="exact"` (Clopper–Pearson) rather than
Wilson. The caption text was written from memory/assumption rather than
from the code that generated the numbers.

**Fix.** The table's own numbers are correct and have not changed. The
caption in `paper/mfd_manuscript.tex` now reads "95% exact
(Clopper–Pearson) binomial confidence interval" instead of "95% Wilson
interval". `verification/05_dmax_sweep_300trials.py` was updated to
compute Clopper–Pearson (not Wilson) for the table it prints, so it now
reproduces Table 2 exactly, including the CI bounds.

## 2. Section 5.5's step-size robustness claim for a=16 was inaccurate

**Finding.** The manuscript stated: "Terminal-state counts were identical
or changed by at most one trial out of ten (a single native/local-trap
reclassification at a=16, h→h/4), and mean relaxation times changed by at
most 5.6%." Independently re-running `verification/06_step_size_robustness.py`
for $a=16$, $D_{\max}=500$ (fully deterministic, same seeds) gives:

| comparison | per-trial reclassifications | mean relaxation time change |
|---|---|---|
| $h \to h/2$ | 2 of 10 (one native→mirror, one mirror→native) | 5.7% |
| $h \to h/4$ | 3 of 10 (two native/mirror swaps + one native→kinetic-trap) | 6.1% |

The "at most one trial" / "5.6%" figures in the original text undercounted
the $a=16$ sensitivity: they were evidently computed by comparing
*aggregate* native/mirror/local-trap counts before and after halving $h$
(which do look nearly unchanged, since two trials swap in opposite
directions and cancel out in the aggregate), not by comparing each trial's
classification individually. The $a\in\{0,1,4,8\}$ cells were unaffected by
this issue — their reported "at most one trial, ≤1.4%" figures are
reproduced exactly.

**Fix.** Section 5.5 of `paper/mfd_manuscript.tex` now reports the $a=16$
case separately and accurately: 2/10 and 3/10 per-trial reclassifications
at $h/2$ and $h/4$ respectively, with the compensating-swap structure
noted explicitly, and relaxation-time changes of 5.7% and 6.1%. The
related summary sentence in Section 3.3 was softened to no longer imply
uniform aggregate-statistic insensitivity across all of $a\in\{0,4,8,16\}$.

## 3. (incidental) A LaTeX syntax error was found and fixed while recompiling

While recompiling to verify the fixes above, `xelatex` reported "Paragraph
ended before \author was complete": the `\author{...}` block was missing
its closing `}` (apparently dropped during an earlier edit that replaced
the corresponding-author email line). This did not affect the PDF's
`pdfauthor` metadata (set independently via `\hypersetup`), but it did
mean the author block on the rendered title page was not being typeset
correctly. Fixed by restoring the closing brace; recompiled cleanly (0
errors) and re-verified that the title page now renders the author block
correctly and that no personal contact information (email, phone, address)
is present anywhere in the compiled PDF text.

## Net effect

No change to the paper's main findings, figures, or any of the headline
numbers (U0, Table 1's τ(a)/slope/D*, Table 2's counts and p-values). Both
fixes are corrections to secondary, specific numerical claims in the
supporting robustness text, caught by independently re-running the
committed verification code rather than trusting the originally reported
figures.

## Second independent review (2026-10-09): additional corrections

| Item | Finding (reproduced) | Change |
|---|---|---|
| Fig. 2(b) / Remark 1 | All 32 "non-monotone" cells of the unified step are first-step Newton non-convergence; U never increases. With step bisection all 112 cells are monotone. Splitting increases U in 47 cells. | `scripts/01` now also writes `dg_bisect`, `dg_u_increased`, `split_u_increased`; Fig. 2 has a third category; Remark 1, abstract and caption reworded (the 1.3–2.7× ratio is a solver-convergence range). `data/fig2_data_reference.json` and `SHA256SUMS` updated. |
| Independence of trials | The same ten seeds are used in every D_max cell, so the 60 trials per a are not independent. Seed-level sign test (`scripts/05`, Table 2b): a=0 8:2, p=0.109; other a not significant. | Manuscript no longer claims a significant a=0 bias; new Table 3 (seed-level); abstract, §5.2, limitations, conclusion revised. |
| Threshold robustness (§5.5) | rmsd_fold=0.3 changes native 6→3 at (a=0, D_max=200). | Text corrected; "threshold-robust" removed. |
| Order of accuracy | p=2.00±0.02 holds for a=0 over the full range; for a=4 only for h ≤ 2^-8; on the Go model p≈2 is recovered only for a=0. | §3.3 and abstract corrected. |
| Slope vs U0 | a=16: −3.0 SE; a=8: 1.7 SE (not >2). | Text corrected. |
| Table 2, a=8 p-value | 0.683 (was 0.684). | Corrected. |
| §6.3 pilot numbers | Script output 0.458±0.004 (a=1), 0.001±0.004 (a=0). | Manuscript updated to the script values. |
| `scripts/06` docstring | Stale "at most one trial / 5.6%". | Updated. |

## Terminology clarification: MIRROR_TRAP and KINETIC_TRAP (2026-10-09)

Names, figures, tables and scripts are unchanged; only their meaning is clarified (new paragraph
"Meaning of the labels" in the manuscript section on terminal-state diagnosis).

- `MIRROR_TRAP` is not an energetic trap. By the exact reflection symmetry of the Go-model
  potential, the mirror state is a minimum of the same energy as the native state
  (U = 0 for both to machine precision). "Trap" is a convenience word; the label is determined by
  the basin (RMSD to the mirror structure), and implies no energy barrier or energy difference.
- `KINETIC_TRAP` is assigned when the energy plateaus away from both native and mirror. The plateau
  test is a moving window on U and does not use the gradient norm, so the class can include
  trajectories stalled near a saddle point (small gradient). The decision depends on the
  thresholds, so borderline misclassification is possible (see the threshold-sensitivity results,
  `scripts/07_threshold_sensitivity.py`, `docs/sensitivity_analysis.md`).

## Third review follow-up (2026-10-09)

- `scripts/01` now really writes `dg_bisect`, `dg_u_increased` and `split_u_increased` into
  `fig2_data.json`; `data/fig2_data_reference.json` (new SHA-256 in `data/SHA256SUMS`) holds all five grids.
- §3.3: the a=0/a=4 order values (p = 2.012 … 2.017; 3.06, 2.30, 2.08, 2.02 for a=4) come from a comparison with a fine
  reference solution (`scripts/02`), not from successive differences; the text now says so. The Go-model values come
  from the Richardson self-convergence test (`scripts/04`).
- Data availability: the manuscript now says the repository will be archived on Zenodo with a DOI inserted at
  release (no DOI exists yet), consistent with the README.

## Reflection equivariance (scripts/10_reflection_equivariance.py)

The dynamics commutes with the reflection R: x -> (-x, y, z) for every a (U depends on distances only; G and A act on
the bead index). Reflecting the initial chain therefore maps NATIVE <-> MIRROR_TRAP exactly. Verified for a = 0, 4, 16,
seeds 0-9, D_max = 500: 30/30 runs swap labels with identical time, U history and final coordinates. `simulate_dg` gained an
optional `reflect_x0` argument (default False; default behaviour and all committed data are unchanged).
