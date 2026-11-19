---
canon: mass-envelope
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: max-mass-level-flight, max-mass-lift-off
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
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
  airplane_to: airplane-takeoff
outputs:
  m_max_level: max-mass-level-flight
  m_max_to: max-mass-lift-off
embeds:
  - stall-speed.clean
  - stall-speed.takeoff
  - motor-propeller-equilibrium
  - advance-ratio-from-speed
  - propeller-table-lookup
  - thrust-at-airspeed-from-coefficient
variables: [aircraft-mass, flight-speed]
optional: [r_m, i_0]
cost: minutes
preconditions:
  - {id: takeoff_speed_above_stall_speed, parameter: v_to, on_violation: error}
  - {id: current_mass_positive, parameter: m_current, on_violation: error}
---

# Mass envelope — what narrows with the take-off mass

**Canonical form**

```
m_max,level:  maximize m   s.t.  exists V, alpha, n_prop:  L = m g,  T(V, n_prop) >= D(V, alpha)
m_max,TO:     maximize m   s.t.  at V_TO(m), take-off configuration:  L = m g,  T - D >= 0
```

**Produces** [[max-mass-level-flight]] · [[max-mass-lift-off]]  ·  **from** [[airplane]] · [[components]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[stall-speed-takeoff]] · [[takeoff-speed]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[airplane-takeoff]] · [[aircraft-mass]] · [[motor-efficiency]]

**Embeds** `stall-speed.clean` (the stall problem at each mass, where the speed scan of the level problem starts, gh-1419) and `stall-speed.takeoff` (the stall problem at each mass, for `V_TO(m)`), and the four propulsion relations; the level-flight drag and the full-throttle thrust are those of `max-level-speed`, evaluated at each mass.

**Kind: an optimisation problem family, swept over the mass** (maintainer, 2026-10-02 —
replaces the payload question: payload is *"how much mass may be added"*). Everything that
narrows with the take-off mass, as curves over `m` ([[performance-over-mass]], split off, gh-1420), and the masses at which it closes (this entry):

**A long run** (maintainer-approved plan of epic #1173, 2026-10-14): computed only on explicit request
(K28), hence `cost: minutes`.

**Variables of the envelope** (#1181): the mass `m`, scanned, and the speed `V`, solved in each
embedded problem. The load factor is not one: the embedded stall problems bind `n = 1` themselves.

- **Speed range and climb.** `V_S(m)` rises, `V_max(m)` falls and `ROC_max(m)` falls with the mass; where the range closes is `m_max,level` — beyond it no level flight is possible, and the climb is zero there. The curves are the entry [[performance-over-mass]].
- **Lift-off — the overloaded-bomber limit.** Whether the aircraft can still climb at its
  take-off speed in take-off configuration: `m_max,TO`, where the excess thrust at `V_TO(m)`
  vanishes. It lies **below** `m_max,level`: an aircraft can still cruise and yet no longer climb
  out of the lift-off. (`V_TO(m)` keeps the take-off reserve: `V_TO(m) = V_S,TO(m) · V_TO/V_S,TO`.)
- **Trim.** The centre-of-gravity range over the mass is the entry [[cg-envelope]] (split off, gh-1420).

**Source.** 🟢 Sadraey §11.6.3 (§12.5.4 and Eq. 12.90, the trim over the speed range, belong to [[cg-envelope]] since gh-1420); the level-flight
and climb problems as in ANFORDERUNGEN §3.10 (this canon's requirements document, not a Sadraey section).

**Validity in the RC/UAV regime (ADR 0028).** The scan is regime-independent as a construction; each root carries the limitation of the problem it embeds. The stall speed behind `V_TO(m)` inherits the Reynolds sensitivity of `C_L,max` (Anderson §4.3; Lennon Ch. 1–3), and since `V_S ∝ √m` the chord Re moves along the scan, which the polar must follow. For a hand-launched model `V_TO` is the throw speed, with no ground roll and no wheel brakes; whether `T − D ≥ 0` at that speed is the right lift-off criterion for hand launch has no source [no source].

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/mass_envelope.py` | DEVIATES | 🟡 checked by a hand check, a brute-force scan over the mass and an independent fast-tier solution; not validated against a measurement, the motor data are marked test values | `m_max,level` is the root over the mass of the best excess thrust over the speed, `G(m) = max_V (T − D)` with `L = m g`; `m_max,TO` is the root of `T − D` at `V_TO(m) = V_S,TO(m) · V_TO / V_S,TO` in the take-off configuration. Both: an upward scan of the mass from the current mass, each step `mass_envelope_step` (30 percent) more than the one before, to the first mass at which the quantity is not positive, then Illinois regula falsi. **Deviations:** (1) no IPOPT problem is posed (the torque balance is a bisection on the propeller table); (2) the embedded optimisations are shared functions (`PoweredFlight`, `maximise_over_speed`, `OptiAdapter.stall`, `first_extremum_check`), not relations handed out by `Context.embedded` (ARCHITECTURE ch. 8.12 defers that form; the four propulsion relations are handed out); the embedded stall check `optimum_at_first_cl_peak` runs on every stall solve; (3) the state must hold at the current mass, else `no_feasible_speed` (no downward search). Route B, complete data only (a missing `R_m`, `I_0` or propeller table is `missing_input`). |

No register node is mapped to this entry.

**What is requestable (#1420).** Both outputs. The curves and the trim range are the entries [[performance-over-mass]] and [[cg-envelope]], not implemented.

**Implementation remark (#1420) — what closes the bracket.** The scan goes up from the current mass. At a mass above the current one, two outcomes mean "the data end" and close the bracket without a sign change: for `m_max,level` the failure `no_feasible_speed` (no speed inside the propeller table at which the wing carries the weight), for `m_max,TO` the failure `outside_propeller_table` (the lift-off speed is beyond the table). The edge between the last mass that evaluates and the first that does not is bisected to `powered_root_tolerance` of the mass, the last mass that evaluates is the answer, and the notice `powered_limit_declared` with `limit = evaluation_edge` says so (ADR 0020). Every other failure (a stall solve that does not converge, a stall off the first lift peak, a missing input, any failure at the current mass) is not "not held": it surfaces with the mass of the scan in the message and in `detail.mass_kg`.

**Implementation remark (#1420) — warnings, assumptions.** Warnings forwarded: those of the answer's level-flight point at `m_max,level` (flap, Reynolds, Mach and the drag notice of the adapter), those of the stall solve and the level-flight point of the answer at `m_max,TO` (with the flap-validity declaration), the route notice once, the skipped speeds of the level answer, and `powered_limit_declared` where the best excess lies at the stall corner; the warnings of the iterates are not forwarded. Assumptions: `G(m)` and `T − D` at `V_TO(m)` fall with the mass and cross zero once (bracketed by the upward scan); the best excess has one maximum over the speed (golden section). A state still held at the last mass of the scan (`mass_envelope_max_steps`) is `not_converged`.

**Measured (gh-1420, Avistar Elite 3.70 kg, marked test motor values):** `m_max,level` 17.82 kg, `m_max,TO` 17.82 kg (5 g below); the whole run 43 s. A stall solve of `stall-speed` fails for masses from 8.8 to 9.4 kg on this aircraft (#1423), which the scan inherits.

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
