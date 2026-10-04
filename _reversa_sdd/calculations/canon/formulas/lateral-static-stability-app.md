---
canon: lateral-static-stability-app
entry: formula
uncertainty: interval
kind: procedure
tool: AB
shape: law
status: draft
output: dihedral-effect-app, weathercock-stability-app, spiral-criterion-app
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

# Static lateral-directional stability on approach

**Canonical form**

```
solve for alpha at V:   L = m * g          (V = V_app)
C_l_beta, C_n_beta, C_l_r, C_n_r := AeroBuildup(airplane, x_ref = x_CG, V, alpha).run_with_stability_derivatives()
E_spiral = C_l_beta * C_n_r - C_n_beta * C_l_r
```

**Produces** [[dihedral-effect-app]] · [[weathercock-stability-app]] · [[spiral-criterion-app]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[centre-of-gravity]] · [[approach-speed]]

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

**Uncertain (A11 rule 5) — reclassified 2026-10-03 on the Urmodell fleet; maintainer confirmation
pending.** The same day this entry was kept crisp on two aircraft, with the condition "revisit if a spiral
criterion lies near zero". The 74-aircraft fleet (`reference_fleet/urmodell/ERGEBNISSE.md` B3) triggers it:
the spiral verdict differs between AeroBuildup and AVL on 24 of 74 aircraft, the sign of `C_nβ` on 15 (all
flying wings without fin or with a centre fin; rerun 2026-10-04 after a generator fix). Worlds: **AeroBuildup** and **AVL**. AeroBuildup is **not a valid world for
`C_lβ` of swept wings**: it has no sweep contribution to the dihedral effect (`sweep_clb_repro.py`: a plain
wing at C_L 0.4 gives +0.001 at 0°, 17° and 30° sweep, AVL −0.032 / −0.057 / −0.076). For swept
layouts the interval of `C_lβ` and of the spiral criterion therefore rests on AVL alone and is marked not
validated, as for the neutral point. V-tail `C_nβ`: AeroBuildup about 2× AVL, cause not shown (🟡 missing
mutual interference of the two halves).

**Open before trusting the numbers.** Whether AeroBuildup captures the dihedral effect of the
wing position (high vs low wing) and the fin in the fuselage wake is unchecked — a cross-check
with AVL on BRYAN is required for approval.

**Source.** 🟢 Sadraey Eqs 12.5–12.6 (static signs), §12 spiral mode (criterion).
