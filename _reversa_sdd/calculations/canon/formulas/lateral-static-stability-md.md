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

**AVL cross-check on BRYAN (2026-10-03, `bryan_lateral_avl.py`).** `C_lβ` agrees within 20 %
(AeroBuildup −0.055, AVL −0.066), so the high-wing dihedral effect is captured in magnitude. `C_nβ`
without fuselage agrees roughly (0.103 vs 0.119); **with fuselage AeroBuildup halves it** (0.050),
AVL barely changes (0.122) — AVL models bodies crudely, so the fuselage share stays open (needs a third
source). The spiral criterion is negative in all methods (weakly unstable), magnitudes differ ×10.
AeroBuildup's *local* roll damping is about twice AVL's and ASB VLM's (−0.82 vs −0.35/−0.36 at V_md); the
steady roll rate of [[max-roll-rate]] nevertheless agrees with AVL within 23 % (nonlinear, see there).

**Open before trusting the numbers.** Whether AeroBuildup captures the dihedral effect of the
wing position (high vs low wing) and the fin in the fuselage wake is unchecked — a cross-check
with AVL on BRYAN is required for approval.

**Source.** 🟢 Sadraey Eqs 12.5–12.6 (static signs), §12 spiral mode (criterion).
