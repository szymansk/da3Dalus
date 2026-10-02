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
the speed where it flies level, so no Reynolds numbers of different speeds are mixed.

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
