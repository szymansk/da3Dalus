---
canon: lateral-static-stability-mp
entry: formula
kind: procedure
tool: AVL
shape: law
status: approved
output: dihedral-effect-mp, weathercock-stability-mp, spiral-criterion-mp, spiral-doubling-time-mp, roll-due-to-yaw-rate-mp
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  x_cg: centre-of-gravity-design
  v: minimum-sink-speed
outputs:
  c_l_beta: dihedral-effect-mp
  c_l_r: roll-due-to-yaw-rate-mp
  c_n_beta: weathercock-stability-mp
  e_spiral: spiral-criterion-mp
  t2_spiral: spiral-doubling-time-mp
---

# Static lateral-directional stability at the minimum-sink speed

**Canonical form**

```
solve for alpha at V:   L = m * g          (V = V_mp)
C_l_beta, C_n_beta, C_l_p, C_n_p, C_l_r, C_n_r := AVL(airplane incl. fuselage BODY, x_ref = x_cg_design, V, alpha)  # stability-axis derivatives
E_spiral    = C_l_beta * C_n_r - C_n_beta * C_l_r
lambda_s    = -(g / V) * E_spiral / (C_l_beta * C_n_p - C_n_beta * C_l_p)   # spiral root, no inertias
T_2,spiral  = ln 2 / lambda_s    if lambda_s > 0   (time to double; stable spiral: no doubling, report T_half)
```

**Produces** [[dihedral-effect-mp]] · [[roll-due-to-yaw-rate-mp]] · [[weathercock-stability-mp]] · [[spiral-criterion-mp]] · [[spiral-doubling-time-mp]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[centre-of-gravity-design]] · [[minimum-sink-speed]]

**Kind: a procedure — derivatives from one solver evaluation.** The dihedral effect `C_lβ`
(roll stability; negative rights the aircraft), the weathercock stability `C_nβ` (positive turns
the nose into the wind) and the spiral criterion `E_spiral` (positive: the spiral is stable — a
banked aircraft levels itself; Sadraey §12.3.3 spiral mode, the constant term of the lateral
quartic). All of them need derivatives only, no inertias: the spiral mode is quasi-static, its root
follows from the derivatives alone (Etkin & Reid, spiral approximation 🟡 equation to be cited from the
book). Dutch roll and roll time constant need inertias and stay out (dynamics later).
The time to double is what Sadraey limits (§12.3.3, Tab. 12.15, class I: ≥ 12–20 s level 1, ≥ 8 s
level 2, ≥ 4 s level 3); the sign alone is not a requirement — most aircraft are mildly spirally
unstable (Drela, desrules). The bands belong to the evaluation (A10).

**Third operating point (maintainer decision 2026-10-26, #1309).** The same procedure as
[[lateral-static-stability-md]] and [[lateral-static-stability-app]], evaluated at `V_mp`, the circling
condition: a glider thermalling flies near minimum sink, where `C_L` is about `√3` times that at `V_md`
(parabolic polar), so `C_lβ` and `C_lr` are larger and the spiral criterion differs. This is the speed at
which a spiral tightening in the turn matters; the evaluation decides by control layout which value governs.

**Added output (maintainer decision 2026-10-27, #1275).** The roll derivative with yaw rate
[[roll-due-to-yaw-rate-mp]] (`C_lr`), which the procedure already evaluates for the spiral criterion, is now also
an output: [[turn-sideslip]] needs `κ = −C_lr/C_lβ` from the same AVL run (one producer, ADR 0022). Output added by
maintainer decision 2026-10-27, #1275; the entry's approval is unchanged.

**Values, not verdicts (A10).** The RC bands — dihedral 2–7° by wing position and control,
Lennon's spiral-stability margin by class — belong to the evaluation.

**One tool for every aircraft: AVL (K27, maintainer 2026-10-05).** Lateral derivatives come from AVL with the
fuselage as BODY, for all layouts, marked **not validated**. No geometry-dependent tool switch: one authority
per quantity (ADR 0022). Why (`reference_fleet/urmodell/ERGEBNISSE.md` B3, B8):
- **AeroBuildup is outside its validity** for `C_lβ` of swept wings (no sweep term; plain wing at C_L 0.4:
  +0.001 at 0/17/30° sweep, AVL −0.032/−0.057/−0.076) and for `C_nβ` of V-tails (≈ 2× AVL; physics: side
  force ∝ sin²ν with panel interference, which AVL contains). Sweep is no small effect: 17° at C_L 0.3–0.5
  ≈ 1.5–2° dihedral (Scholz §7.1: 10° sweep ≈ 1° dihedral; Sadraey §5.11: ∝ sin 2Λ). On conventional, T and
  cross tails AeroBuildup agrees with AVL (spiral verdict 38 of 39) and stays as a cross-check there.
- **ASB's VLM is no substitute:** it has the sweep term but misses the base term of `C_lβ` (0.000 vs AVL
  −0.032 on the plain unswept wing) and has no fuselage; spiral verdict vs AVL differs on 46 of 74.
- Not uncertain in the A11 sense any more: only one valid world remains. Being the only one, AVL is
  unvalidated — calibration against flown aircraft (spiral test, Lennon) is open.

**Source.** 🟢 Sadraey Eqs 12.5–12.6 (static signs), §12.3.3 spiral mode (criterion), §12.3.3 Tab. 12.15
(time to double). 🟡 Etkin & Reid spiral-root approximation (to be cited by equation number).

**Validity in the RC/UAV regime (ADR 0028).** The relations are scale-free: the static signs of `C_lβ` and `C_nβ` (Sadraey Eqs 12.5–12.6) and the spiral criterion, unstable when `|C_lβ·C_nr| < |C_lr·C_nβ|` (Sadraey §12.3.3). Mach ≤ 0.3 needs no correction (Anderson §1.10.3). The limit is the single tool: AVL is inviscid and attached with no stall (Budziak, Table 2.1), meant for thin surfaces "at small angles of attack and sideslip", and its slender-body fuselage has "relatively limited" experience and is to be used "with caution" (`avl_doc.txt:99-119`), consistent with the open fuselage share of `C_nβ`. At `V_mp` the flow is attached, but at chord Re below 7·10⁴ laminar separation is the normal state (Anderson §20.3.2), and AVL has no viscous term to see it [no source for the effect on the derivatives]. The AeroBuildup block above judges sweep and V-tail sideslip terms, not Reynolds number; below chord Re 7·10⁴ no world is validated, and calibration against flown aircraft stays open. The Table 12.15 doubling times are MIL-F-8785C criteria for piloted aircraft, their RC applicability is [no source], and they belong to the evaluation (A10).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/lateral_static_stability_mp.py` | EXACT | 🟢 | the derivatives come from one AVL run (`aero_kernel/solvers/avl.py`, `lateral_derivatives`) at `C_L = m g / (½ ρ V² S_ref)` with the kernel's `S_ref`, the moment and rotation reference at the design CG (y, z from the airplane), the fuselages as BODY. AVL's body is round and axisymmetric on a straight axis, so each fuselage is the round body of the same section area (the super-ellipse area, upper and lower half with their own exponents) on the axis through the area-weighted section centres (`aero_kernel/solvers/avl_body.py`); declared as `avl_body_equivalent_round`. `E = C_lβ·C_nr − C_nβ·C_lr`, `λ_s = −(g/V)·E/(C_lβ·C_np − C_nβ·C_lp)` from AVL's derivatives (both per `p'b/2V`, `r'b/2V`), `T_2 = ln 2/λ_s` for `λ_s > 0`; for `λ_s < 0` the halving time `−ln 2/|λ_s|`, negative, declared as `spiral_halving_time_reported`; no finite time (`λ_s = 0`, zero denominator) is an error. `C_lr` (per `r'b/2V`) is also output (decision 2026-10-27, #1275). No refined-mesh check of the lateral derivatives. Per neutral-point world, because the moment reference is the design CG |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [x] **Convergence** — the criterion, and what is returned and declared on failure
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-26): the approved AVL procedure of [[lateral-static-stability-md]] and
> [[lateral-static-stability-app]] at a third operating point, V_mp — the circling condition, where C_L is about
> √3 times that at V_md (decision #1309: the spiral while thermalling governs rudder-only aircraft). Same
> outputs (C_lβ, C_nβ, spiral criterion, doubling time), AVL with the fuselage as BODY, moment reference at the
> design CG; same declared limits (inviscid, crude body, not validated below chord Re 7·10⁴; Etkin & Reid
> spiral-root equation number still 🟡). Bands belong to the evaluation (A10). No kernel implementation yet.
