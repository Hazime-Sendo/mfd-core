# Order-of-accuracy verification (summary)

Method: self-convergence (Richardson). The step size is halved repeatedly and the ratio
`||x(h_k) - x(h_k/2)||` of successive differences is expected to approach `2^p` for a method of
order `p` (no external reference solution needed). Scripts: `scripts/02`, `03`, `04`.

**(A) Smooth, single-well, non-commuting test problem** (anisotropic quartic potential,
non-uniform `G`, non-commuting `A = a sqrt(G) J sqrt(G)`, `a = 0, 4`): over nine step halvings
(`h = 2^-3 ... 2^-11`) the observed order is `p = 2.00 +/- 0.02`, as expected for a discrete-gradient
generalisation of the implicit midpoint rule.

**(B) Go-model landscape (`n = 20`, multiple minima).** For sufficiently small `h` (roughly
`h <~ 2^-10`) the order is again `p ~ 2`. For coarser `h` the apparent order is irregular and can be
negative. This is not an integrator defect: with several basins (native, mirror, local traps), a
small change in `h` can send a trajectory into a different basin, so `||x(h) - x(h/2)||` measures a
discrete jump between basins ("discrete attractor branching"). Script `03` reproduces the
long-time (`T = 2`) behaviour; script `04` the near-equilibrium self-convergence study.

**Step-size robustness of the production runs (`h = 5e-3`).** Individual trajectories are
step-size sensitive, so the statistics were checked directly (`scripts/06`): at `D_max = 500`,
halving `h` leaves the aggregate terminal-state counts and the mean relaxation time nearly
unchanged for `a = 0, 1, 4, 8` (<= 1.4 % change in mean time); at `a = 16` the per-trial
classification is more sensitive (see `docs/manuscript_corrections.md` and the log in
`results/logs/06_step_size_robustness.log`). Monotonicity (`dU < 0` at every step) held in every case.
