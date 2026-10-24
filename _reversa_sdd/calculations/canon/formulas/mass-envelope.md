---
canon: mass-envelope
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: speed-range-over-mass, climb-rate-over-mass, max-mass-level-flight, max-mass-lift-off, cg-envelope-over-mass
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
inputs:
  airplane: airplane
  components: components
  m_current: aircraft-mass
  g: gravity
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  v_s_to: stall-speed-takeoff
  v_to: takeoff-speed
  x_np: neutral-point
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
  airplane_to: airplane-takeoff
  airplane_ldg: airplane-landing
  delta_e_up: elevator-deflection-up
  delta_e_down: elevator-deflection-down
outputs:
  speed_range: speed-range-over-mass
  roc_curve: climb-rate-over-mass
  m_max_level: max-mass-level-flight
  m_max_to: max-mass-lift-off
  cg_envelope: cg-envelope-over-mass
embeds:
  - stall-speed.clean
  - stall-speed.landing
  - stall-speed.takeoff
  - max-level-speed
  - best-rate-of-climb
  - motor-propeller-equilibrium
  - advance-ratio-from-speed
  - propeller-table-lookup
  - thrust-at-airspeed-from-coefficient
variables: [aircraft-mass, flight-speed]
optional: [r_m]
cost: minutes
---

# Mass envelope — what narrows with the take-off mass

**Canonical form**

```
for each mass m (a sweep; the airplane's mass is one point of it):
  V_S(m), V_max(m)          stall-speed problem / max-level-speed problem at mass m
  ROC_max(m)                best-rate-of-climb problem at mass m
  m_max,level:  maximize m   s.t.  exists V, alpha, n_prop:  L = m g,  T(V, n_prop) >= D(V, alpha)
  m_max,TO:     maximize m   s.t.  at V_TO(m), take-off configuration:  L = m g,  T - D >= 0
  x_fwd(m):     most forward x_CG trimmable at the stall, landing configuration, elevator at delta_e,up
  x_aft(m):     most aft x_CG trimmable at V_max(m), elevator at delta_e,down     (both given design inputs)
```

**Produces** [[speed-range-over-mass]] · [[climb-rate-over-mass]] · [[max-mass-level-flight]] · [[max-mass-lift-off]] · [[cg-envelope-over-mass]]  ·  **from** [[airplane]] · [[components]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[stall-speed-takeoff]] · [[takeoff-speed]] · [[neutral-point]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[airplane-takeoff]] · [[airplane-landing]] · [[elevator-deflection-up]] · [[elevator-deflection-down]] · [[aircraft-mass]] · [[motor-efficiency]]

**Kind: an optimisation problem family, swept over the mass** (maintainer, 2026-10-02 —
replaces the payload question: payload is *"how much mass may be added"*). Everything that
narrows with the take-off mass, as curves over `m`, and the masses at which it closes:

**A long run** (maintainer-approved plan of epic #1173, 2026-10-14): computed only on explicit request
(K28), hence `cost: minutes`.

**Variables of the envelope** (#1181): the mass `m`, swept, and the speed `V`, solved in each
embedded problem. The load factor is not one: the embedded stall problems bind `n = 1` themselves.

- **Speed range.** `V_S(m)` rises, `V_max(m)` falls; where they meet is `m_max,level` — beyond
  it no level flight is possible.
- **Climb.** `ROC_max(m)` falls with the mass and is zero at `m_max,level`.
- **Lift-off — the overloaded-bomber limit.** Whether the aircraft can still climb at its
  take-off speed in take-off configuration: `m_max,TO`, where the excess thrust at `V_TO(m)`
  vanishes. It lies **below** `m_max,level`: an aircraft can still cruise and yet no longer climb
  out of the lift-off. (`V_TO(m)` keeps the take-off reserve: `V_TO(m) = V_S,TO(m) · V_TO/V_S,TO`.)
- **Trim.** The CG range `[x_fwd(m), x_aft(m)]` in which the elevator, **at the given deflections** `δ_e,up` / `δ_e,down`, trims
  the aircraft over its whole speed range (Sadraey Eq. 12.90: trim from `V_S` to `V_max` at both
  CG extremes): `δ_e,up` at the slow end (stall, landing configuration), `δ_e,down` at the fast
  end (`V_max(m)`). The neutral point stands beside it as the physical stability boundary; the
  canon reports which edge comes first and judges nothing (A10). A load `Δm` at `x_load` moves the
  CG by `Δm·(x_load − x_CG)/(m + Δm)` — whether that stays inside is read off, not computed here.

**How the front edge is solved (BRYAN, 2026-10-02).** Hold the angle of attack at the stall angle
`α_S(m)` of the stall-speed problem and leave the speed free: with the elevator at `δ_e,up` the tail
download raises the trimmed stall speed, so trimming at the clean `V_S` is infeasible. Bound
`x_CG < x_NP`: with the elevator at its given deflection, `Cm = 0` has a second root aft of the neutral point (the unstable
branch). For a conventional tail the aft edge from the elevator at `δ_e,down` at `V_max` lies far behind the
neutral point (BRYAN: > 90 % MAC), so the neutral point is the edge that comes first.

**Front edge across methods (BRYAN, 2026-10-03, `bryan_fwd_trim_avl.py`):** AeroBuildup 14.3 % MAC, AVL
10.4 % (CLAF thickness rule) and 13.5 % (CLAF 1.0). AeroBuildup lacks the wing downwash at the tail,
which *helps* the download at the front edge, so it is conservative here. AVL lacks the profile drag of the deflected
surface, which AeroBuildup carries only as a Hoerner drag factor on the clean section (no flap separation;
`kulfan_airfoil.py:211-255`). The two errors run in opposite directions 🟡 INFERRED — the conclusion
rested on AeroBuildup carrying NeuralFoil's low-Re flap losses, a premise the #1181 correction withdrew,
so it is not re-established (open, STAND §10); spread 10.4–14.3 % MAC. **Kept crisp (A11 rule 5, maintainer 2026-10-03):** the front edge is computed with
AeroBuildup, which is conservative here. **Validity condition, declared (ADR 0020):** methods carrying the
wing–tail downwash place the front edge up to about 4 % MAC further forward. Revisit if a reference aircraft
shows a first-flight reserve of the order of that spread.

**Absorbs** `forward-cg-limit` (2026-10-02): its value is this envelope's front edge at the
current mass — a separate entry would be a second authority (ADR 0022).

**Validity conditions, declared (ADR 0020).** The tail must not itself be stalled at the trim
points; ground effect is not modelled (optimistic in the flare); at model scale the elevator works
at low Reynolds number, and AeroBuildup represents its deflection only as an effective-angle shift on the
clean airfoil with a Hoerner drag factor (no flap separation, δ range of the fit unknown; `kulfan_airfoil.py:211-255`).

**Source.** 🟢 Sadraey §11.6.3, §12.5.4, Eq. 12.90 (trim over the speed range); the level-flight
and climb problems as in §3.10.

**Validity in the RC/UAV regime (ADR 0028).** The sweep is regime-independent as a construction; each curve carries the limitation of the problem it embeds. `V_S(m)` inherits the Reynolds sensitivity of `C_L,max` (Anderson §4.3; Lennon Ch. 1–3), and since `V_S ∝ √m` the chord Re moves along the sweep, which the polar must follow. The trim edges rest on AeroBuildup, which ignores main-wing downwash on the horizontal tail and so over-predicts tail effectiveness (Sharpe 2024 §5.4), consistent with the declared 10.4–14.3 % MAC spread. Above about 30° of elevator deflection the flow over the horizontal tail separates (Sadraey §12.5.4, context of Eq. 12.90), which bounds the "tail not stalled" condition the entry declares. For a hand-launched model `V_TO` is the throw speed, with no ground roll and no wheel brakes; whether `T − D ≥ 0` at that speed is the right lift-off criterion for hand launch has no source [no source].

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
