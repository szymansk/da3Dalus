---
canon: parabolic-polar-fit
entry: formula
kind: fit
tool: OPT
cost: seconds
shape: law
status: draft
output: zero-lift-drag-coefficient, oswald-efficiency
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/fit
  - status/draft
tex: \min_{C_{D0},\,e}\; \sum_{i} \Big( C_{D,i} - C_{D0} - \frac{C_{L,i}^2}{\pi\,AR\,e} \Big)^2 \quad C_{L,i} \in \big[\max(0.1,\,0.1\,C_{L,max}),\; 0.85\,C_{L,max}\big]
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  ar: aspect-ratio
  cl_max: max-lift-coefficient
outputs: {cd0: zero-lift-drag-coefficient, e_osw: oswald-efficiency}
---

# Parabolic polar fitted to the solver polar (ADR 0026)

**Canonical form**

```
minimize over C_D0, e_osw:   sum_i ( C_D,i - C_D0 - C_L,i^2 / (pi * AR * e_osw) )^2
points i: the solver polar along level flight (L = m * g, each point at its own speed),
          C_L,i in [ max(0.1, 0.1 * C_L,max),  0.85 * C_L,max ]
```

**Produces** [[zero-lift-drag-coefficient]] · [[oswald-efficiency]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[aspect-ratio]] · [[max-lift-coefficient]]

**Kind: a fit — a least-squares parabola over the operating `C_L` window** (window from
BR-16). `C_D0` is the fitted zero-lift parasite drag and `e` the Oswald factor in
Anderson's sense (§6.7.2) — comparable with literature values. Each polar point is taken at
the speed where it flies level, so each point carries its own Reynolds number; the fit spans points at different speeds and therefore at different Reynolds numbers.

**Display only — never an input to performance** (ADR 0026). The analysis computes with the
solver drag directly. These two numbers serve the user and the **calculated value** of the
`cd0` design assumption, compared against its estimate (ADR 0010). The **fit residual** is
reported: it says how non-parabolic the polar is.

**Replaces** `parasite-drag-split` (ADR 0004's one-point decomposition at cruise, amended by
ADR 0026): with AeroBuildup's empirical `e` that decomposition was "all drag except the
estimated induced drag at the cruise `C_L`", not parasite drag, and it hung on the open
cruise speed. Before it, `zero-lift-drag-from-sweep` and `reynolds-scheduled-polar` — both
gone with the false cycle.

**Source.** 🟢 Anderson §6.7.2 (drag polar, Oswald factor); ADR 0026; window BR-16.

**Validity in the RC/UAV regime (ADR 0028).** The parabola is an empirical approximation even at full scale: parasite drag varies with lift, and the Oswald factor absorbs that variation (Anderson §6.7.2). At low Reynolds number the variation is large, because laminar separation and transition change section drag with angle of attack (Anderson §20.3.2, qualitative); the polar can then depart from a parabola, and the fit residual measures how far. A low fitted `e` then partly reflects viscous drag, not induced drag: it is a display value, not a Trefftz-plane span efficiency. Along the level-flight polar Re falls as C_L rises (V ∝ C_L^-½), so the fitted C_D0 belongs to that flight path, not to one Reynolds number. Mach ≤ 0.3: no wave drag, no correction.

**The solver drag it is fitted to (#1346, maintainer 2026-11-03).** The solver polar's `C_D` is the kernel's
drag of AeroBuildup, `(D_profile + k_e,D0 · D_induced) / (q·S_ref)` ([[aerobuildup-evaluation]]): AeroBuildup's
full-scale viscous factor `k_e,D0` is taken out of its induced drag, because NeuralFoil's section polars already
contain the lift-dependent profile drag. The fitted `e` is therefore no longer lowered twice for that drag; on
the four fleet aircraft of the #1346 measurement (level-flight sweep, this entry's window, sea level) it rises by
+11.5 … +15.7 % (BRYAN 0.665 → 0.769, WIESEL 0.542 → 0.611, CHEKKER 0.621 → 0.711, BELEMNITOS 0.501 → 0.559), `C_D0`
unchanged. Still a display value, not a Trefftz-plane span efficiency.

**Method, window and rejection (#1401).** The points are `fit_points` values of `C_L` equally spaced over the
window `[max(window_cl_floor, window_lower_fraction · C_L,max), window_upper_fraction · C_L,max]`; each is flown
at the speed where `L = m g` (`V = sqrt(2 m g / (ρ S_ref C_L))`), at the angle of attack where AeroBuildup's lift
equals the weight at that speed, on the branch before the main `C_L` peak (the highest local maximum, [[stall-speed]], #1423). The fit is ordinary least squares of
`C_D` on `C_L²` (intercept `C_D0`, slope `k`), `e = 1/(π AR k)`. The window, the point count and the bound on `e`
are the parameters of the rule `parabolic-polar-fit` (`rules.yaml`); the window is BR-16's. **Resolution goes up,
thresholds never move:** `fit_points` is the lever for a poor fit, and no threshold on the residual exists. **The
fit is not refused for being poor:** every fit declares its residual (RMS and largest deviation of the solver's
`C_D` from the parabola, `C_L` and speed range; notice `polar_fit_residual`). **A fit that is not physically
meaningful is declared and returned, never replaced:** a slope `k ≤ 0` (so `e ≤ 0`), a `C_D0 ≤ 0`, or an `e`
above `max_oswald` (1, Anderson §5.3.3) gives the warning `polar_fit_nonphysical` of severity `error` with the
fitted numbers in its `detail`; the formulas that divide by them ([[induced-drag-factor]], the probes) refuse a
non-positive `e` by their own preconditions. The only refusals of the fit itself are an empty window, a level
that the airplane does not reach before its main `C_L` peak, a point whose lift does not settle on the weight,
a solver drag at or below zero, and a slope of zero to `opt_zero_span` (no finite `e`): each is a `FormulaError`, never a
value. The refusals carry the codes `empty_fit_window`, `invalid_fit_points` (a point count that is no integer of at least 3), `defective_solver_drag` (any point with `C_D ≤ 0`, before anything is divided by it) and `not_converged`. The kernel's drag is declared as everywhere (`induced_drag_viscous_factor_removed`).

**Cost (measured, #1401).** The fit is the slowest formula of the kernel that is not a long run: 48 points take about 10 s (RV-7) to 90 s (WIESEL) on the reference fleet, about 40 s on BRYAN (one AeroBuildup sweep and a few evaluations per point). The cost class is declared `seconds` (`cost: seconds`, tens of seconds); the class `minutes` would skip the fit, and everything that reads it, unless the caller asks for long runs (ARCHITECTURE §8.7).

**Regime warnings.** The regime of the fit is that of its slowest and its fastest point: Reynolds number (chord times V over the kinematic viscosity) and Mach number (V over the speed of sound) rise strictly with V, so the bands are met first at one of the two extremes.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/parabolic_polar_fit.py` | EXACT | 🟢 | least-squares parabola over `fit_points` level-flight points of the solver polar (OPT adapter `level_polar`, one AeroBuildup sweep and secant refinement per point, #1401); the nonphysical-fit declaration and the residual notice are the formula's own |

No register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Model and domain** — the fitted form and where it may be evaluated are stated
- [ ] **Rejection** — when the fit is refused rather than used
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
