---
canon: aileron-deflection-required
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: approved
output: aileron-deflection-required-cruise, aileron-deflection-required-approach
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - direction/design
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
tex: \delta_{a,req}:\; L(V,\alpha) = m\,g, \quad C_{roll}\big(V,\alpha,\,\delta_{a,req},\,p_{target}\big) = 0
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v: null
  p_target: null
outputs: {delta_a_req: null}
applications:
  - id: cruise
    bind: {v: cruise-speed-target, p_target: roll-rate-target-cruise}
    produce: {delta_a_req: aileron-deflection-required-cruise}
    given: [roll-rate-target-cruise, cruise-speed-target]
    when: has_aileron
  - id: approach
    bind: {airplane: airplane-landing, v: approach-speed, p_target: roll-rate-target-approach}
    produce: {delta_a_req: aileron-deflection-required-approach}
    given: [roll-rate-target-approach]
    when: has_aileron
worlds: [aerobuildup, avl]
---

# Aileron deflection a roll-rate target needs

> **Uncertain quantity (A11, maintainer 2026-10-03).** Interval over two method worlds, each run through
> the whole entry: **AeroBuildup** (the optimisation as written below; the deflection as an effective-angle shift `τ·δ` on the clean airfoil with a Hoerner drag factor — no flap separation — and strip-wise
> roll damping without induced relief, strongly nonlinear at real roll rates) and **AVL** (steady roll with
> the ailerons driven directly, `d1 d1 delta`, CLAF by ASB's thickness rule; carries the induced relief
> but no low-Re flap losses). Neither is provably conservative. BRYAN, approach, ailerons ±20°:
> p·b/2V AeroBuildup 0.339, AVL 0.276 (`reference_fleet/bryan_roll_rate_compare.py`). The 23 % spread
> can flip "target met" (A9), so A11 rule 5 makes it an interval. ASB's VLM models no control deflection
> and is not a world.

**AVL world, valid only for `|pb/2V| ≤ 0.10` (decision (b) (maintainer, 2026-10-25, #1243): "a würde das Intervall verfälschen und dann ist nicht klar, welche Grenze belastbar ist", finding #1181).** AVL is linear in δ by construction (`Avl/src/amake.f:1184-1187`, "linearize about zero deflection"), and its primer gives `−0.10 < pb/2V < 0.10` as the practical limit for roll rates, beyond which results "should be interpreted with caution" (`Avl/avl_doc.txt:121-141`). The BRYAN AVL value `pb/2V = 0.276` lies outside it. **Decision (b):** the check is on the roll-rate target: the AVL world solves `δ_a,req` for the target `p_target`, so it is excluded when `|p_target·b/2V|` at that application's speed exceeds 0.10. The AeroBuildup world is unaffected (its own maximum is still `target_above_method_maximum`). No kernel implementation exists yet (0 implementations); the rule is binding for it. Inside the range the interval spans both worlds; outside it the quantity is the AeroBuildup world alone, and the AVL world is not used — its value is not part of the interval. The exclusion is declared, never silent (ADR 0020, ADR 0027 point 8): the warning `world_outside_validity` names the world and carries the AVL value and the limit. The range is exactly the stated one: `|pb/2V| = 0.10` is inside. If AeroBuildup fails, the quantity is an error as before (a failed world is never dropped).

**Canonical form**

```
solve for alpha, delta_a,req (steady roll at V, roll rate held at the target):   L(V, alpha) = m * g,   C_roll(V, alpha, delta_a,req, p_target,cruise | p_target,app) = 0
evaluated at V = V_cruise,target (when given) and at V = V_app, for each roll-rate target given
world aerobuildup:  search delta_a upward from 0 until p(delta_a) stops increasing; a target above that maximum
                    has no solution in this world (target_above_method_maximum, with the maximum roll rate and
                    its delta_a); never a clipped angle
world avl:          linear in delta; delta_a,req solved directly
```

**Produces** [[aileron-deflection-required-cruise]] · [[aileron-deflection-required-approach]]  ·  **from** [[airplane]] · [[airplane-landing]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]] · [[approach-speed]] · [[roll-rate-target-cruise]] · [[roll-rate-target-approach]]

**The approach application binds the landing configuration (maintainer decision 2026-10-26, #1212: "v_app mit Klappen").** `V_app = k · V_S,LDG` comes from the landing configuration, so `δ_a,req` at that speed is solved on `airplane-landing` — the flaps at `flap-deflection-landing` ([[airplane-configuration]]) — not on the clean `airplane`; the cruise application stays on the clean airplane. For a flaperon the landing deflection is the symmetric bias and `δ_a` is applied antisymmetrically on top; the details and the declared caveats are those of [[roll-rate]]. Without flaps `airplane-landing` is the airplane itself. (Binding change only; the entry's status is unchanged.)

**Kind: a procedure — a closure by a prescribed value.** The steady roll: the rolling moment from the ailerons balances the roll damping, lift carries the weight. One symmetric aileron angle ±δ_a; an up/down differential is not modelled (out of the MVP, maintainer 2026-10-01).

**Decided (maintainer, 2026-10-14):** every control device is an angle; the stops are never referenced — the canon finds which deflection a wanted roll rate needs (supersedes the 2026-10-01 statement that throws are construction parameters).

**Measured against a target.** Its companion [[roll-rate]] gives the roll rate at a given aileron deflection, without a target.

**Two answers per operating point, split over two entries.**
- `p` — the roll rate at the given aileron deflection `δ_a`. A property of the airplane at that angle.
- `δ_a,req` — the aileron deflection a roll-rate target needs ([[aileron-deflection-required]]). In the AeroBuildup world `δ_a` is searched upward from 0 until `p(δ_a)` stops increasing; a target above that maximum has no solution in this world — the error `unsupported_configuration`, code `target_above_method_maximum`, with the maximum roll rate and its `δ_a` in the detail, never a clipped angle (A10, ADR 0020). In the AVL world, linear in δ, `δ_a,req` is solved directly.

**The requirement names its speed (A2).** At fixed deflection `pb/2V` is nearly independent of speed, so the roll rate in °/s grows with `V`. "Roll rate at cruise" is the character statement RC pilots make; "roll rate on approach" is the controllability statement where Sadraey sizes the aileron (§12.3.3, Phase C — slowest, fewest °/s per degree). Either requirement may be given; each is checked at its own speed.

**AeroBuildup is adequate here** — unlike for adverse yaw. Aileron rolling moment (section lift from NeuralFoil on the clean airfoil at `α + τ·δ`) and roll damping (roll rate in the local onset flow, `aero_buildup.py:719-731`) both come from lift, not from induced drag. AVL can cross-check.

**Method premise (architect, 2026-10-14).** AeroBuildup has no flap model of its own: it evaluates the clean airfoil at `α + τ·δ`, `τ = 1 − x_hinge^2.7514` (a δ-independent fit to an XFoil study), with the drag times a multiplier fitted to Hoerner, *Fluid Dynamic Drag*, p. 13-13 Fig. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255`, via `aero_buildup.py:784-801`). There is no flap separation: it over-predicts the effectiveness at large δ until the clean section stalls, and the δ range of the τ fit is unknown. AVL is linear in δ by construction and documented only for `|pb/2V| < 0.10`. Reference point: Sadraey §12.4.3 — beyond about 20–25° deflection, flow separates over the aileron and effectiveness drops; recommendation `|δ_A,max| ≤ 25°`. Transport and GA material, not checked at model Reynolds number (ADR 0028). Beyond 25° the formula reports a `practice` warning with the angle (ARCH §8.8); the canon sets no limit.

**Source.** 🟢 Sadraey §12.4 (aileron design): the aileron rolling moment `C_l = C_lδA·δA` (§12.4.2, Eq. 12.23) and the linear roll damping `C_lp` per `pb/2V` with the roll mode (§12.3.3). The linear balance `C_l,δa · δa + C_l,p · pb/2V = 0` is **not** printed by Sadraey: his §12.4.2 steady roll is a quadratic rolling-drag balance (Eq. 12.37); the linear form combines his two terms, and both worlds solve `C_roll = 0` directly, with the rate requirement made scale-free per the domain expert (time-to-bank does not transfer to model scale).

**Validity in the RC/UAV regime (ADR 0028).** The steady-roll balance is scale-free: the aileron moment `C_l = C_lδA·δA` (Sadraey §12.4.2, Eq. 12.23) balances the roll damping, and the rate enters only as `pb/2V`. Mach ≤ 0.3 needs no correction (Anderson §1.10.3). The regime bites in the deflected section, not in the relation: laminar flow at low chord Re separates readily — Anderson's laminar case at Re_c = 10⁵ separates on both surfaces (§20.3.2) — and neither world contains it. AVL is inviscid, attached and gives no stall (Budziak, Table 2.1); AeroBuildup's τ is a δ-independent XFoil fit without flap separation, and NeuralFoil signals such inputs only through its analysis confidence (Sharpe 2024 §7.2.4). Sadraey puts aileron stall beyond about 20–25° (§12.4.3, Table 12.19), transport/GA material; where it starts at model Re is [no source]. Declared limitation (finding #1181, decided (b)): the AVL world is linear in δ and used only for `−0.10 ≤ pb/2V ≤ 0.10` (`avl_doc.txt:121-141`); beyond it the interval is the AeroBuildup world alone, with the AVL value in the `world_outside_validity` warning (BRYAN 0.276 lies beyond). Aileron differential and adverse yaw are not modelled (out of the MVP).

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
> (AeroBuildup), strip-wise roll damping without induced relief, nonlinear at real roll rates. Stage 2 is open on `roll-rate-target-approach` (no data source — no app field yet). The
> implementation checklist item holds vacuously: no aero_kernel formula for this entry yet (roll-rate is
> implemented).
