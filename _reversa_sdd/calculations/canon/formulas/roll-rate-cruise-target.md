---
canon: roll-rate-cruise-target
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: approved
output: roll-rate-cruise
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
  v_cruise_target: cruise-speed-target
  delta_a: aileron-deflection
outputs: {p: roll-rate-cruise}
applications:
  - id: at_cruise_speed_target
    given: [cruise-speed-target]
    when: has_aileron
worlds: [aerobuildup, avl]
---

# Roll rate at the mission's cruise speed

> **Uncertain quantity (A11, maintainer 2026-10-03).** Interval over two method worlds, each run through
> the whole entry: **AeroBuildup** (the optimisation as written below; the deflection as an effective-angle shift `τ·δ` on the clean airfoil with a Hoerner drag factor — no flap separation — and strip-wise
> roll damping without induced relief, strongly nonlinear at real roll rates) and **AVL** (steady roll with
> the ailerons driven directly, `d1 d1 delta`, CLAF by ASB's thickness rule; carries the induced relief
> but no low-Re flap losses). Neither is provably conservative. BRYAN, approach, ailerons ±20°:
> p·b/2V AeroBuildup 0.339, AVL 0.276 (`reference_fleet/bryan_roll_rate_compare.py`). The 23 % spread
> can flip "target met" (A9), so A11 rule 5 makes it an interval. ASB's VLM models no control deflection
> and is not a world.

**AVL world, valid only for `|pb/2V| ≤ 0.10` (decision (b) (maintainer, 2026-10-25, #1243): "a würde das Intervall verfälschen und dann ist nicht klar, welche Grenze belastbar ist", finding #1181).** AVL is linear in δ by construction (`Avl/src/amake.f:1184-1187`, "linearize about zero deflection"), and its primer gives `−0.10 < pb/2V < 0.10` as the practical limit for roll rates, beyond which results "should be interpreted with caution" (`Avl/avl_doc.txt:121-141`). The BRYAN AVL value `pb/2V = 0.276` lies outside it. **Decision (b):** the AVL world is excluded when its own result `|pb/2V|` at the cruise-speed target exceeds 0.10. Inside the range the interval spans both worlds; outside it the quantity is the AeroBuildup world alone, and the AVL world is not used — its value is not part of the interval. The exclusion is declared, never silent (ADR 0020, ADR 0027 point 8): the warning `world_outside_validity` names the world and carries the AVL value and the limit. The range is exactly the stated one: `|pb/2V| = 0.10` is inside. If AeroBuildup fails, the quantity is an error as before (a failed world is never dropped).

**Canonical form**

```
solve for alpha, p at V_cruise,target (steady roll, at the given aileron deflection):   L = m * g,   C_roll(V, alpha, delta_a, p) = 0
```

**Produces** [[roll-rate-cruise]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]] · [[aileron-deflection]]

**Kind: a procedure**, the same steady roll as [[roll-rate]], evaluated at `V_cruise,target`.
**Only when a cruise-speed target is given** (maintainer, 2026-10-02). Without one, the approach
check and the dimensionless roll rate `p·b/2V` of [[roll-rate]] remain — for an RC model without
a cruise requirement the latter is the character statement, since it hardly depends on speed.

**Method premise (architect, 2026-10-14).** AeroBuildup has no flap model of its own: it evaluates the clean airfoil at `α + τ·δ`, `τ = 1 − x_hinge^2.7514` (a δ-independent fit to an XFoil study), with the drag times a multiplier fitted to Hoerner, *Fluid Dynamic Drag*, p. 13-13 Fig. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255`, via `aero_buildup.py:784-801`). There is no flap separation: it over-predicts the effectiveness at large δ until the clean section stalls, and the δ range of the τ fit is unknown. AVL is linear in δ by construction and documented only for `|pb/2V| < 0.10`. Reference point: Sadraey §12.4.3 — beyond about 20–25° deflection, flow separates over the aileron and effectiveness drops; recommendation `|δ_A,max| ≤ 25°`. Transport and GA material, not checked at model Reynolds number (ADR 0028). Beyond 25° the formula reports a `practice` warning with the angle (ARCH §8.8); the canon sets no limit.

**Source.** 🟢 Sadraey §12.4.2: the aileron rolling moment `C_l = C_lδA·δA`, with `C_lδA` from strip integration over the aileron span (Eq. 12.23), and the steady roll where the aileron moment equals the roll resistance (Eq. 12.37, which Sadraey writes as a quadratic rolling drag, not a linear derivative); the linear roll damping `C_lp` per `pb/2V` appears with the roll mode (§12.3.3). The canon uses neither closed form: both worlds solve `C_roll = 0` directly, so the citation covers the relation and the numbers come from the solvers. Evaluating at `V_cruise,target`, only when that target is given, is the maintainer's decision (2026-10-02).

**Validity in the RC/UAV regime (ADR 0028).** The same steady roll as [[roll-rate]], with the same qualification: the balance is scale-free in `pb/2V` (Sadraey §12.3.3, §12.4.2), and Mach ≤ 0.3 needs no correction (Anderson §1.10.3). At the cruise-speed target the chord Re is higher than on approach, so the low-Re separation argument (Anderson §20.3.2) bites less. Neither world models aileron separation, and the large-δ loss Sadraey gives beyond about 20–25° (§12.4.3) is unchecked at model Re [no source]. Declared limitation (finding #1181, decided (b)): the AVL world is linear in δ and used only for `−0.10 ≤ pb/2V ≤ 0.10` (`avl_doc.txt:121-141`); beyond it the interval is the AeroBuildup world alone, with the AVL value in the `world_outside_validity` warning (BRYAN 0.276 lies beyond). Aileron differential and adverse yaw are not modelled (out of the MVP).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

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

> **Approved — stage 1** (maintainer, 2026-10-25): the steady-roll balance (L = m·g, aileron moment
> against roll damping) as an interval over the AeroBuildup and AVL worlds (A11), with decision (b) of
> #1243 — outside |pb/2V| ≤ 0.10 the AVL world is excluded and its value shown only in the warning
> (`world_outside_validity`). Declared limits: aileron as an effective-angle shift without flap separation
> (AeroBuildup), strip-wise roll damping without induced relief, nonlinear at real roll rates. Stage 2 complete. The
> implementation checklist item holds vacuously: no aero_kernel formula for this entry yet (roll-rate is
> implemented).
