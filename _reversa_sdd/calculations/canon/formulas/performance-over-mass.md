---
canon: performance-over-mass
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: speed-range-over-mass, climb-rate-over-mass
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
  m_max_level: max-mass-level-flight
  g: gravity
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs:
  speed_range: speed-range-over-mass
  roc_curve: climb-rate-over-mass
embeds:
  - stall-speed.clean
  - max-level-speed
  - best-rate-of-climb
  - motor-propeller-equilibrium
  - advance-ratio-from-speed
  - propeller-table-lookup
  - thrust-at-airspeed-from-coefficient
variables: [aircraft-mass, flight-speed]
optional: [r_m, i_0]
cost: minutes
---

# Performance over the mass — the speed range and the climb rate as curves

**Split off from `mass-envelope` (gh-1420).** The entry `mass-envelope` produced these two curves beside the
two largest masses. The curves are not requestable (a curve is not a result of the kernel yet) and the two masses
need none of them, so they are their own entry; the text below is the part of the `mass-envelope` entry that
concerns them, moved unchanged. The sweep runs from the current mass up to the largest mass of level flight,
which [[mass-envelope]] produces (`m_max_level`): this entry reads it and does not solve it again.

**Canonical form**

```
for each mass m of the sweep, from the current mass up to m_max,level (the airplane's mass is one point of it):
  V_S(m), V_max(m)          stall-speed problem / max-level-speed problem at mass m
  ROC_max(m)                best-rate-of-climb problem at mass m
```

**Produces** [[speed-range-over-mass]] · [[climb-rate-over-mass]]  ·  **from** [[airplane]] · [[components]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[max-mass-level-flight]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[aircraft-mass]] · [[motor-efficiency]]

**Embeds** `stall-speed.clean`, `max-level-speed` and `best-rate-of-climb`, each evaluated at the masses of the sweep (the embedded problems, not their output quantities), and the four propulsion relations they use.

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

**Validity in the RC/UAV regime (ADR 0028).** Each curve carries the limitation of the problem it embeds. `V_S(m)` inherits the Reynolds sensitivity of `C_L,max` (Anderson §4.3; Lennon Ch. 1–3), and since `V_S ∝ √m` the chord Re moves along the sweep, which the polar must follow.

**Source.** 🟢 the level-flight and climb problems as in ANFORDERUNGEN §3.10 (this canon's requirements document, not a Sadraey section).

## Implementations (0)

None in aero_kernel; no register node is mapped to this entry. **Blocked (gh-1420):** a curve is not a result of the kernel yet (ARCHITECTURE ch. 8.3), so nothing could read it, and complete but unreachable code is not kept (ADR 0021). It also needs the sweep to solve the speed searches inside the window near `m_max,level`, which is narrower than the scan step of `max-level-speed` and `best-rate-of-climb`.

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
