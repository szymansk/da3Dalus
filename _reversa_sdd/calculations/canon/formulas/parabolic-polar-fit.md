---
canon: parabolic-polar-fit
entry: formula
kind: fit
tool: OPT
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

**Produces** [[zero-lift-drag-coefficient]] · [[oswald-efficiency]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[aspect-ratio]] · [[max-lift-coefficient]]

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

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

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
