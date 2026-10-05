---
canon: lateral-static-stability-app
entry: formula
kind: procedure
tool: AVL
shape: law
status: draft
output: dihedral-effect-app, weathercock-stability-app, spiral-criterion-app, spiral-doubling-time-app
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
C_l_beta, C_n_beta, C_l_p, C_n_p, C_l_r, C_n_r := AVL(airplane incl. fuselage BODY, x_ref = x_CG, V, alpha)  # stability-axis derivatives
E_spiral    = C_l_beta * C_n_r - C_n_beta * C_l_r
lambda_s    = -(g / V) * E_spiral / (C_l_beta * C_n_p - C_n_beta * C_l_p)   # spiral root, no inertias
T_2,spiral  = ln 2 / lambda_s    if lambda_s > 0   (time to double; stable spiral: no doubling, report T_half)
```

**Produces** [[dihedral-effect-app]] · [[weathercock-stability-app]] · [[spiral-criterion-app]] · [[spiral-doubling-time-app]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[centre-of-gravity]] · [[approach-speed]]

**Kind: a procedure — derivatives from one solver evaluation.** The dihedral effect `C_lβ`
(roll stability; negative rights the aircraft), the weathercock stability `C_nβ` (positive turns
the nose into the wind) and the spiral criterion `E_spiral` (positive: the spiral is stable — a
banked aircraft levels itself; Sadraey §12 spiral mode, the constant term of the lateral
quartic). All of them need derivatives only, no inertias: the spiral mode is quasi-static, its root
follows from the derivatives alone (Etkin & Reid, spiral approximation 🟡 equation to be cited from the
book). Dutch roll and roll time constant need inertias and stay out (dynamics later).
The time to double is what Sadraey limits (§12.3.3, Tab. 12.15, class I: ≥ 12–20 s level 1, ≥ 8 s
level 2, ≥ 4 s level 3); the sign alone is not a requirement — most aircraft are mildly spirally
unstable (Drela, desrules). The bands belong to the evaluation (A10).

**Two points.** Evaluated at `V_md` and on approach, because `C_lβ` and `C_lr` grow with `C_L`
and `C_nβ` can fall at high angle of attack.

**Values, not verdicts (A10).** The RC bands — dihedral 2–7° by wing position and control,
Lennon's spiral-stability margin by class — belong to the evaluation.

**One tool for every aircraft: AVL (K27, maintainer 2026-10-05).** Lateral derivatives come from AVL with the
fuselage as BODY, for all layouts, marked **not validated**. No geometry-dependent tool switch: one authority
per quantity (ADR 0022). Why (`reference_fleet/urmodell/ERGEBNISSE.md` B3, B8):
- **AeroBuildup is outside its validity** for `C_lβ` of swept wings (no sweep term; plain wing at C_L 0.4:
  +0.001 at 0/17/30° sweep, AVL −0.032/−0.057/−0.076) and for `C_nβ` of V-tails (≈ 2× AVL; physics: side
  force ∝ sin²ν with panel interference, which AVL contains). Sweep is no small effect: 17° at C_L 0.3–0.5
  ≈ 1.5–2° dihedral (Scholz §7.3: 10° sweep ≈ 1° dihedral; Sadraey §5.11: ∝ sin 2Λ). On conventional, T and
  cross tails AeroBuildup agrees with AVL (spiral verdict 38 of 39) and stays as a cross-check there.
- **ASB's VLM is no substitute:** it has the sweep term but misses the base term of `C_lβ` (0.000 vs AVL
  −0.032 on the plain unswept wing) and has no fuselage; spiral verdict vs AVL differs on 46 of 74.
- Not uncertain in the A11 sense any more: only one valid world remains. Being the only one, AVL is
  unvalidated — calibration against flown aircraft (spiral test, Lennon) is open.

**Source.** 🟢 Sadraey Eqs 12.5–12.6 (static signs), §12 spiral mode (criterion), §12.3.3 Tab. 12.15
(time to double). 🟡 Etkin & Reid spiral-root approximation (to be cited by equation number).
