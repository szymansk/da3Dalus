---
canon: turn-sideslip
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: turn-sideslip, turn-sideslip-gain
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: \begin{aligned}\hat r_{max} &= \frac{\rho\,g\,b\,C_{L,mp}}{8\,W/S} \\ \kappa &= -\frac{C_{l,r}}{C_{l,\beta}} \\ \beta_{turn} &= \kappa\,\hat r_{max}\end{aligned}
inputs:
  rho: air-density
  g: gravity
  b_ref: wing-span
  w_s: wing-loading
  c_l_mp: lift-coefficient-minimum-sink
  c_l_beta: dihedral-effect-mp
  c_l_r: roll-due-to-yaw-rate-mp
outputs:
  beta_turn: turn-sideslip
  kappa: turn-sideslip-gain
applications:
  - id: without_aileron
    when: has_no_aileron
preconditions:
  - {id: dihedral_effect_stabilising, parameter: c_l_beta, on_violation: error}
---

# Sideslip in the steady turn (Drela's beta_turn)

**Canonical form**

```
r_hat_max  = rho * g * b_ref * C_L,mp / (8 * W/S)       # worst steady level turn, phi = 45 deg, r_hat = r*b/(2V)
kappa      = -C_l_r / C_l_beta                          # rad;  C_l_beta < 0, both from AVL at V_mp
beta_turn  = kappa * r_hat_max                          # rad, converted to deg
```

**Produces** [[turn-sideslip]] · [[turn-sideslip-gain]]  ·  **from** [[air-density]] · [[gravity]] · [[wing-span]] · [[wing-loading]] · [[lift-coefficient-minimum-sink]] · [[dihedral-effect-mp]] · [[roll-due-to-yaw-rate-mp]]

**Kind: a law.** A closed-form relation over two AVL derivatives and the loading of the aircraft. Applies only to
aircraft **without ailerons** (`has_no_aileron`): with ailerons the inward rolling moment of the curved flight path is
cancelled by a slight outward aileron deflection (Drela, Fig. 9), no sideslip is needed.

**What the turn does (Drela, printed).** In a steady level turn of radius `R` the wing sees a spanwise velocity
variation `u(y) = V (1 - y/R)`; the outer tip flies faster, produces more lift, and the resulting rolling moment steepens
the bank. Without ailerons only a steady sideslip, nose pointing outside the flight circle, rolls the other way
(Figure 10); "smaller dihedral requires larger beta_turn". Drela prints

```
beta_turn ≈ (1/Gamma) * (C_L / (dC_L/dalpha)) * (b / 2R) * sin(phi)        (beta, Gamma in radians),  dC_L/dalpha ≈ 2*pi / (1 + 2/AR)
beta_turn < (beta_turn)max ≈ 5 ... 15 deg                                    (Eq. 11)
```

at the tightest expected turn radius `R`. Eq. 11 is the **band**; the relation for `beta_turn` above it is unnumbered.

**What the canon uses instead — derived, not printed.**

1. *The yaw-rate form.* The velocity variation across the span is the effect of the body yaw rate `r`. In the
   coordinated level turn the angular velocity vector `Omega = V/R` is vertical; the body yaw component is
   `r = Omega * cos(phi)`, so `r_hat = r b/(2V) = (b/2R) cos(phi)`. With `tan(phi) = V^2/(g R)` the same
   quantity is `r_hat = (g b / (2 V^2)) sin(phi)` (coordinated turn: `r = g sin(phi) / V`). The two spellings are one.
2. *Drela's `sin(phi)` is superseded.* Drela's printed `(b/2R) sin(phi)` equals `q b/(2V)`, the **pitch**-rate form,
   which produces no spanwise velocity gradient. 🟡 **Inferred intent:** a `sin(phi)` written for the V-form was carried
   unchanged into the R-form (maintainer decision 2026-10-26, from the expert research on Lab 11 notes p. 6-8; Drela's
   intent cannot be verified). With the turn `C_L` the two coincide only at `phi = 45 deg`.
3. *Removing R: the worst case.* Level turn, lift `L cos(phi) = W` with `C_L` fixed: `V^2 = 2 (W/S) / (rho C_L cos(phi))`.
   Insert into the V-form:
   `r_hat = g b sin(phi) * rho C_L cos(phi) / (4 W/S) = rho g b C_L sin(2 phi) / (8 W/S)`,
   maximal at `phi = 45 deg`: `r_hat_max = rho g b C_L / (8 W/S)`. The tightest turn at the given `C_L` is the one at
   45 deg; with Drela's `sin(phi)` there would be no interior maximum. The result needs no turn radius.
4. *The flight condition* is the minimum-sink lift coefficient `C_L,mp` (maintainer 2026-10-25): the circling condition,
   where the turn is flown slow and `r_hat` is large; held fixed while `phi` varies in step 3.
5. *Roll balance.* Instead of Drela's `(1/Gamma)(C_L/a)` the canon balances the rolling moments of the AVL stability
   derivatives: `C_l_beta * beta + C_l_r * r_hat = 0`, so `beta = kappa * r_hat` with `kappa = -C_l_r / C_l_beta`
   (maintainer decision 2026-10-27, option (a)). Both derivatives are AVL at `V_mp` for every layout (K27):
   `C_l_beta` is [[dihedral-effect-mp]], `C_l_r` is [[roll-due-to-yaw-rate-mp]], both outputs of
   [[lateral-static-stability-mp]]. Drela's `kappa` is about 1 (the `≃`) up to `3π/8 ≈ 1.18` (elliptic strip theory);
   the canon reports the AVL value and does not assume one. `kappa` is an output as well.

**Assumptions.**
- **Roll balance only.** The yaw balance of the sideslipping aircraft (fin, weathercock stability, rudder) is not
  closed; the sideslip is the one that cancels the rolling moment alone.
- **The fuselage is crude in AVL** (slender BODY, used "with caution", `avl_doc.txt:99-119`): the fuselage share of
  `C_l_beta` and `C_l_r` is as uncertain as in [[lateral-static-stability-mp]].
- **No viscous effects.** AVL is inviscid and attached; the drag the sideslip costs (fuselage broadside) is Drela's
  reason for the limit and is not computed.
- **Linear, steady.** Small angles, derivatives at the trim of `V_mp`; the turn itself is quasi-steady (no angular
  accelerations). The changed `C_L` and speed along the 45 deg turn are not re-evaluated in AVL: the derivatives
  stay those at `V_mp`.
- **The band 5...15 deg is Drela's** ("difficult to estimate", "for most aircraft"). It belongs to the evaluation
  (A10), rule `turn-sideslip` in `drela.yaml`; the canon outputs the value only.

**Precondition `dihedral_effect_stabilising` (on `c_l_beta`; error).** `C_l_beta` must be negative. With
`C_l_beta >= 0` there is no roll-stable sideslip balance (zero: division by zero; positive: `kappa` changes sign and
means nothing for the turn), so the value is not computed and the violation is reported.

**Dimensional check.** 🟢 balances by hand: `rho g b` = kg m^-3 · m s^-2 · m = kg m^-1 s^-2; `W/S` = N m^-2 = kg m^-1 s^-2;
the quotient and `C_L` are dimensionless, so `r_hat_max` is dimensionless. `kappa` = (1/rad) / (1/rad), dimensionless;
`beta = kappa * r_hat` is an angle in rad (radian is a dimensionless unit), converted to degrees by `180/π` for the output.
Example: `b` = 2 m, `W/S` = 30 N/m^2, `C_L` = 1, `rho` = 1.225 kg/m^3, `g` = 9.81 m/s^2 → `r_hat_max` = 1.225 · 9.81 · 2 · 1 / (8 · 30) = 0.1001;
for `kappa` = 1: `beta_turn` = 0.1001 rad = 5.74 deg.

**Source.** 🟡 PARTIAL — 🟢 Drela, MIT 16.Unified, *Design Rules*, "Dihedral Sizing Criteria - Steady Sideslip in Turns",
p. 6-8 (the mechanism, the unnumbered `beta_turn` relation, Eq. 11 for the band); the coordinated-turn kinematics
(`r = g sin(phi) / V`, steps 1-3) and the 45 deg worst case are **derived here**, not printed — Drela's printed `sin(phi)`
is superseded (🟡, step 2); `kappa` from AVL (K27, `reference_fleet/urmodell/ERGEBNISSE.md` B3, B8), maintainer decision
2026-10-27, #1275. Draft: adopts nothing until the maintainer approves.

**Validity in the RC/UAV regime (ADR 0028).** The kinematics and the roll balance are scale-free (Mach ≤ 0.3 needs no
correction, Anderson §1.10.3). The limit is the single tool: AVL is inviscid and attached with no stall, so at `V_mp`
and chord Re below 7·10⁴ — where laminar separation is the normal state (Anderson §20.3.2) — the derivatives carry an
error [no source for its size]. Drela's 5...15 deg is for full-scale-like aircraft; its RC applicability is [no source],
and it belongs to the evaluation.

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
