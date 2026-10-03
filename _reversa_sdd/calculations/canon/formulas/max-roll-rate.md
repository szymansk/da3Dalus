---
canon: max-roll-rate
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: draft
output: max-roll-rate-approach, max-roll-rate-nondimensional
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: L(V,\alpha) = m\,g, \quad C_{roll}\big(V,\alpha,\,\delta_{a,max},\,p_{max}\big) = 0
---

# Maximum roll rate with the aileron throws set in the airplane

> **Uncertain quantity (A11, maintainer 2026-10-03).** Interval over two method worlds, each run through
> the whole entry: **AeroBuildup** (the optimisation as written below; viscous flap model, but strip-wise
> roll damping without induced relief, strongly nonlinear at real roll rates) and **AVL** (steady roll with
> the ailerons driven directly, `d1 d1 delta`, CLAF by ASB's thickness rule; carries the induced relief
> but no low-Re flap losses). Neither is provably conservative. BRYAN, approach, ailerons ±20°:
> p·b/2V AeroBuildup 0.339, AVL 0.276 (`reference_fleet/bryan_roll_rate_compare.py`). The 23 % spread
> can flip "target met" (A9), so A11 rule 5 makes it an interval. ASB's VLM models no control deflection
> and is not a world.

**Canonical form**

```
solve for alpha, p_max (steady roll at V, full set throw):   L(V, alpha) = m * g,   C_roll(V, alpha, delta_a,max, p_max) = 0
evaluated at V = V_app;   p_hat_max = p_max * b_ref / (2 * V_app)
```

**Produces** [[max-roll-rate-approach]] · [[max-roll-rate-nondimensional]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[approach-speed]]

**Kind: a procedure — a closure by a prescribed value.** The steady roll: the rolling moment from the ailerons balances the roll damping, lift carries the weight. `s` scales the **throws set in the airplane** — up and down as constructed, a differential included — from 0 to the full throw.

**The throws are construction parameters, not results** (maintainer, 2026-10-01). `delta_a,max` up and down (`positive/negative_deflection_deg` on the trailing-edge device) are fixed by the construction: clearance at the aileron, servo kinematics, horn placement. The canon checks against them; it does not size them.

**A property of the airplane — no target involved.** Its companion [[aileron-throw-fraction]] measures a target against the same steady roll.

**Two answers per operating point, split over two entries.**
- `p_max` — the roll rate the set throws deliver. A property of the airplane.
- `s_req` — the fraction of the set throw the requirement needs. `s_req ≤ 1`: reachable, and the rest is reserve (a dual rate or expo can take it away). `s_req > 1`, or no solution: **not reachable with these throws** — declared, never clipped (ADR 0020).

**The requirement names its speed (A2).** At fixed throw `pb/2V` is nearly independent of speed, so the roll rate in °/s grows with `V`. "Roll rate at cruise" is the character statement RC pilots make; "roll rate on approach" is the controllability statement where Sadraey sizes the aileron (§12.3.3, Phase C — slowest, fewest °/s per degree). Either requirement may be given; each is checked at its own speed.

**AeroBuildup is adequate here** — unlike for adverse yaw. Aileron rolling moment (section lift from NeuralFoil with the deflection) and roll damping (roll rate in the local onset flow, `aero_buildup.py:719-731`) both come from lift, not from induced drag. AVL can cross-check. Declared limit: NeuralFoil's flap model at large throws and low Reynolds number is unvalidated, and aileron stall beyond about 25° (Sadraey §12.4.3) is only as good as that model.

**Source.** 🟢 Sadraey §12.4 (aileron design; steady roll from `C_l,δa · δa + C_l,p · pb/2V = 0`), with the rate requirement made scale-free per the domain expert (time-to-bank does not transfer to model scale).

**2026-10-02:** evaluated on approach only; the cruise value moved to
[[max-roll-rate-cruise-target]] and exists only when a cruise-speed target is given. New output
`p_hat_max = p·b/2V` — nearly independent of speed, the RC character statement without a reference
speed.
