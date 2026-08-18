---
canon: air-density-isa
entry: formula
kind: law
shape: law
status: draft
output: air-density
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
---

# ISA air density at altitude

**Canonical form**

```
rho = rho_ISA(h)   [U.S. 1976 COESA standard atmosphere]
```

**Produces** [[air-density]]  ·  **from** [[altitude]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. Not a procedure. rho_ISA(h) is a closed form — the barometric formula over a piecewise-linear lapse-rate table, closed with the ideal gas law. AeroSandbox even ships that exact closed form (`method='isa'`, _isa_atmo_functions.py:62). It was classified as a procedure only because the formula sits behind a library call the parser could not read. Caveat worth keeping in the canon: no call site in this repo passes `method=`, so every rho in the app comes from the *default* `method='differentiable'` path, which is a cubic-B-spline surrogate of that law, not the law itself — see `method` and `convergence` below.

**Evaluated by.** Cubic B-spline interpolation over a fixed knot table (a table lookup with a named interpolation scheme). aerosandbox/atmosphere/_diff_atmo_functions.py:10-44 builds 38 knot altitudes spanning −5.0e6 … +2.087e6 m, evaluates the exact ISA at each, and fits `InterpolatedModel` to T(h) and to log p(h); pressure_differentiable = exp(spline(log p)). density() then divides. Selected by `method='differentiable'`, the constructor default (atmosphere.py:32) — and every one of the 15 call sites in this repo (app/api/utils.py:26, app/services/analysis_service.py:626 and :1728, app/services/operating_point_generator_service.py:661/717/769/884, mass_cg_service.py:280, section_aoa_service.py:451/506, neuralfoil_cdcl_service.py:21, avl_trim_service.py:99, aerobuildup_trim_service.py:100) constructs `asb.Atmosphere(altitude=...)` with no `method` argument, so the exact-ISA path is never taken.

**Accuracy.** No iteration and therefore no convergence criterion — a single direct evaluation. The guarantee is: exact at the knots, spline truncation error between them. Measured in this venv (poetry run, differentiable vs method='isa'): 0 ppm at h = 0, 5000 and 10000 m (all knots); −61 ppm at 100 m; −339 ppm at 500 m; −739 ppm at 1000 m; −1535 ppm at 2000 m; −1987 ppm (−0.20%) at 3000 m; +7943 ppm (+0.79%) at 7500 m. Note the library's 0.02% figure is for *pressure*; density is roughly ten times worse at 3 km because the p and T interpolation errors do not cancel in p/(R·T). At RC/UAV altitude the consequence on any speed is ≤0.1% (V ∝ rho^−1/2), which is far inside the uncertainty of every other input in this register.

**On failure.** Silent NaN outside the knot hull — measured: `asb.Atmosphere(altitude=3e6).density()` → nan, `-6e6` → nan, no exception raised. Silent number outside the class's own declared valid range — `Atmosphere(altitude=100000).density()` returns 4.34e-07 with `_valid_altitude_range == (0, 80000)`. Neither case is declared: no DesignWarning is emitted at any of the 15 call sites, and the app validates altitude on only one schema field (app/schemas/aeroanalysisschema.py:159, `ge=0.0`); :249, :352 and :418 are unbounded floats. Reachability is the mitigating fact — the hull is ±2000 km, so no plausible user input reaches NaN.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> NOAA/NASA/USAF, "U.S. Standard Atmosphere, 1976", NOAA-S/T 76-1562 (the COESA model). Below 32 km identical to the ICAO ISA. Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.6.2 states the troposphere layer used: T(h) = 288.15 - 0.0065*h[m] for 0<=h<=11 km, T = 216.65 K for 11-20 km, pressure from the hydrostatic equation.

**The source writes it as**

```
Scholz does not write rho(h) directly; he writes T(h) and derives p(h), then uses q/M^2 = (gamma/2)*p(h). Sea-level anchors: T0 = 288.15 K, p0 = 101325 Pa, rho0 = 1.225 kg/m^3.
```

**Validity at 0.5–15 kg.** Model is exact and the chain defaults to h=0, so it degenerates to the 1.225 literal. The real RC limitation is not altitude but that RC flies in the surface layer where the day's density deviates from ISA: 15 C vs 30 C at sea level is ~5% in rho, i.e. ~2.5% on every speed in the chain. ISA-at-0m is a nominal reference, not the field condition, and should be labelled as such (ADR 0020: substituting ISA for measured conditions is an undeclared substitution).

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[air_density_rho]] | EXACT | 🟢 |  |
| [[rho-speed-polar]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

