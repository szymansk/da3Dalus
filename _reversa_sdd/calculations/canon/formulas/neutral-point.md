---
canon: neutral-point
entry: formula
kind: procedure
tool: AB
shape: law
status: draft
output: neutral-point
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Neutral point of the airplane

> **⚠ Blocking finding, 2026-10-03 (reference fleet, GH #1154):** AeroBuildup models each surface's
> self-downwash only, not the wing's downwash at the tail (`aero_buildup.py:746`). Its `x_np` lies about
> **10 % MAC aft** of AVL: BRYAN 43.7 vs 33.1 %, e-Hawk 58.4 vs 48.8 %; ASB VLM (no fuselage) 38.3 % on
> BRYAN. The tool of this entry must change to a vortex-lattice method (ASB VLM or AVL), with the fuselage
> contribution declared. Maintainer decision pending; every entry downstream of `x_NP` (static margin,
> cg-for-target-margin, the mass envelope's aft edge) inherits it.

**Canonical form**

```
solve for alpha at V_md:   L(V_md, alpha) = m * g
x_NP := AeroBuildup(airplane, V_md, alpha).run_with_stability_derivatives()['x_np']
```

**Produces** [[neutral-point]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]]

**Kind: a procedure — one solver evaluation at a named point.** AeroBuildup returns the
neutral point directly (`x_np`, from the finite-difference derivatives; ANFORDERUNGEN §3.12).

**Named point: `V_md`** (2026-10-02). The neutral point depends only weakly on the angle of
attack (ADR 0004 §x_np; Anderson §4.9), so one representative level-flight point suffices;
`V_md` is the canon's named mid-range point. A dependence large enough to matter would show
in the Probe at other speeds.

**No feedback from the CG.** The moment reference does not move `x_NP` — measured: 0.17 mm
over 150 mm of reference shift (§2.3). The entry therefore takes no CG input, and the
design relation `x_CG = x_NP − SM_target · c̄` closes no loop.

**Source.** 🟢 Anderson §4.9 / Scholz (neutral point definition); AeroSandbox
`run_with_stability_derivatives`.
