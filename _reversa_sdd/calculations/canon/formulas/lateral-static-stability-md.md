---
canon: lateral-static-stability-md
entry: formula
kind: procedure
tool: AB
shape: law
status: draft
output: dihedral-effect-md, weathercock-stability-md, spiral-criterion-md
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

# Static lateral-directional stability at the minimum-drag speed

**Canonical form**

```
solve for alpha at V:   L = m * g          (V = V_md)
C_l_beta, C_n_beta, C_l_r, C_n_r := AeroBuildup(airplane, x_ref = x_CG, V, alpha).run_with_stability_derivatives()
E_spiral = C_l_beta * C_n_r - C_n_beta * C_l_r
```

**Produces** [[dihedral-effect-md]] · [[weathercock-stability-md]] · [[spiral-criterion-md]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[centre-of-gravity]] · [[minimum-drag-speed]]

**Kind: a procedure — derivatives from one solver evaluation.** The dihedral effect `C_lβ`
(roll stability; negative rights the aircraft), the weathercock stability `C_nβ` (positive turns
the nose into the wind) and the spiral criterion `E_spiral` (positive: the spiral is stable — a
banked aircraft levels itself; Sadraey §12 spiral mode, the constant term of the lateral
quartic). All three need derivatives only, no inertias — Dutch roll, roll time constant and
time-to-double stay out (dynamics later).

**Two points.** Evaluated at `V_md` and on approach, because `C_lβ` and `C_lr` grow with `C_L`
and `C_nβ` can fall at high angle of attack.

**Values, not verdicts (A10).** The RC bands — dihedral 2–7° by wing position and control,
Lennon's spiral-stability margin by class — belong to the evaluation.

**Open before trusting the numbers.** Whether AeroBuildup captures the dihedral effect of the
wing position (high vs low wing) and the fin in the fuselage wake is unchecked — a cross-check
with AVL on BRYAN is required for approval.

**Source.** 🟢 Sadraey Eqs 12.5–12.6 (static signs), §12 spiral mode (criterion).
