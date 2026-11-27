---
canon: mass-envelope
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: speed-range-over-mass, climb-rate-over-mass, max-mass-level-flight, max-mass-lift-off
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
  speed_range: speed-range-over-mass
  roc_curve: climb-rate-over-mass
  m_max_level: max-mass-level-flight
  m_max_to: max-mass-lift-off
embeds:
  - stall-speed.clean
  - stall-speed.takeoff
  - max-level-speed
  - best-rate-of-climb
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
for each mass m (a sweep from the current mass up to m_max,level; the airplane's mass is one point of it):
  V_S(m), V_max(m)          stall-speed problem / max-level-speed problem at mass m
  ROC_max(m)                best-rate-of-climb problem at mass m
m_max,level:  maximize m   s.t.  exists V, alpha, n_prop:  L = m g,  T(V, n_prop) >= D(V, alpha)
m_max,TO:     maximize m   s.t.  at V_TO(m), take-off configuration:  L = m g,  T - D >= 0
```

**Produces** [[speed-range-over-mass]] · [[climb-rate-over-mass]] · [[max-mass-level-flight]] · [[max-mass-lift-off]]  ·  **from** [[airplane]] · [[components]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[stall-speed-takeoff]] · [[takeoff-speed]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[airplane-takeoff]] · [[aircraft-mass]] · [[motor-efficiency]]

**Embeds** `stall-speed.clean` (the stall problem at each mass, where the speed scans start, gh-1419), `max-level-speed` and `best-rate-of-climb` (evaluated at the masses of the sweep, for `V_max(m)` and `ROC_max(m)`), and `stall-speed.takeoff` (the stall problem at each mass, for `V_TO(m)`), and the four propulsion relations; the level-flight drag and the full-throttle thrust are those of `max-level-speed`, evaluated at each mass.

**Kind: an optimisation problem family, swept over the mass** (maintainer, 2026-10-02 —
replaces the payload question: payload is *"how much mass may be added"*). Everything that
narrows with the take-off mass, as curves over `m`, and the masses at which it closes:

**Maintainer decision (2026-11-19, gh-1420):** the kernel returns curves as results (gh-1424). `climb-rate-over-mass` is a curve result of this entry. `speed-range-over-mass` (a curve pair) is not requestable yet, pending the maintainer. The trimmable CG range is its own entry [[cg-envelope]] until the kernel has a trim solve.

**A long run** (maintainer-approved plan of epic #1173, 2026-10-14): computed only on explicit request
(K28), hence `cost: minutes`.

**Variables of the envelope** (#1181): the mass `m`, scanned, and the speed `V`, solved in each
embedded problem. The load factor is not one: the embedded stall problems bind `n = 1` themselves.

- **Speed range.** `V_S(m)` rises, `V_max(m)` falls; where they meet is `m_max,level` — beyond
  it no level flight is possible.
- **Climb.** `ROC_max(m)` falls with the mass and is zero at `m_max,level`.
- **Lift-off — the overloaded-bomber limit.** Whether the aircraft can still climb at its
  take-off speed in take-off configuration: `m_max,TO`, where the excess thrust at `V_TO(m)`
  vanishes. It lies **below** `m_max,level`: an aircraft can still cruise and yet no longer climb
  out of the lift-off. (`V_TO(m)` keeps the take-off reserve: `V_TO(m) = V_S,TO(m) · V_TO/V_S,TO`.)
- **Trim.** The centre-of-gravity range over the mass is the entry [[cg-envelope]] (split off, gh-1420).

**Source.** 🟢 Sadraey §11.6.3 (§12.5.4 and Eq. 12.90, the trim over the speed range, belong to [[cg-envelope]] since gh-1420); the level-flight
and climb problems as in ANFORDERUNGEN §3.10 (this canon's requirements document, not a Sadraey section).

**Validity in the RC/UAV regime (ADR 0028).** The sweep is regime-independent as a construction; each curve and each root carries the limitation of the problem it embeds. `V_S(m)` and the stall speed behind `V_TO(m)` inherit the Reynolds sensitivity of `C_L,max` (Anderson §4.3; Lennon Ch. 1–3), and since `V_S ∝ √m` the chord Re moves along the sweep, which the polar must follow. For a hand-launched model `V_TO` is the throw speed, with no ground roll and no wheel brakes; whether `T − D ≥ 0` at that speed is the right lift-off criterion for hand launch has no source [no source].

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/mass_envelope.py` | DEVIATES | 🟡 checked by a hand check, a brute-force scan over the mass and an independent fast-tier solution; not validated against a measurement, the motor data are marked test values | `m_max,level` is the root over the mass of the best excess thrust over the speed, `G(m) = max_V (T − D)` with `L = m g`; `m_max,TO` is the root of `T − D` at `V_TO(m) = V_S,TO(m) · V_TO / V_S,TO` in the take-off configuration. Both: an upward scan of the mass from the current mass, each step `mass_envelope_step` (30 percent) more than the one before, to the first mass at which the quantity is not positive, then Illinois regula falsi. **Deviations:** (1) no IPOPT problem is posed (the torque balance is a bisection on the propeller table); (2) the embedded optimisations are shared functions (`PoweredFlight`, `maximise_over_speed`, `OptiAdapter.stall`, `main_extremum_check`), not relations handed out by `Context.embedded` (ARCHITECTURE ch. 8.12 defers that form; the four propulsion relations are handed out); the embedded stall check `optimum_at_main_cl_peak` runs on every stall solve; (3) the state must hold at the current mass, else `no_feasible_speed` (no downward search). Route B, complete data only (a missing `R_m`, `I_0` or propeller table is `missing_input`). |

No register node is mapped to this entry.

**What is requestable (#1420, new text).** The two masses and `climb-rate-over-mass` (a `curve` quantity, a result since gh-1424: `x` the masses in kg, `y` in m/s). `speed-range-over-mass` is declared `curve_pair`, which is not a result of the kernel: it is computed (its samples are the stall solves and the level-speed searches of the sweep) and not requestable, a request is `non_scalar_result`. Whether it becomes two `curve` quantities (`V_S(m)` and `V_max(m)` over the same masses) is open. The trim range is the entry [[cg-envelope]], not implemented.

**Implementation remark (#1420, new text) — the curves.** `V_S(m)` is the stall solve of each sample mass (with the `stall-speed` check), `V_max(m)` and `ROC_max(m)` are `highest_level_speed` and `best_climb`, the shared functions of `max-level-speed` and `best-rate-of-climb`, evaluated at the sample mass with its clean stall speed. The samples are `mass_envelope_curve_points` equally spaced masses from the current mass up to (not including) `m_max,level`. The last point of the curves is the root, and what it holds depends on the kind of root. Where the root is a sign change of the best excess thrust (Illinois regula falsi), the thrust equals the drag at the best speed there: that is the root condition itself, so the closing `V_max` is the speed of the best excess that the root search found and the closing rate of climb is zero, both holding to the tolerance of the root and neither computed by the shared functions (they cannot be: no excess is left); only `V_S` of the root is computed. Where the root is the edge of the data (see below), the thrust still exceeds the drag there, so the last point is computed like every other sample. A sample whose search fails (for example a window of speeds with an excess narrower than the 2 m/s scan step, which the scan of the two formulas can miss near the root) is a failure of the formula with the mass named, not a skipped point.

**Implementation remark (#1420, new text) — warnings of the samples (ADR 0020).** The answer state of each sample (level flight at `V_max`, the climb at its optimum) is evaluated once more on a scratch context, as each formula does, so the regime, flap and limit warnings of the sample's stall solve, level answer and climb answer are not lost. They are forwarded as summaries: one warning per code and, for a declared limit, per `detail.limit` (a sample can declare two limits under one code, the floor of the climb scan and the vertical climb), with the masses at which it occurred (`detail.masses_kg`, and `detail.by_mass` with the detail of every occurrence; an identical repetition at one mass is listed once). The route notice is left out of the summary (the answers declare it once). Warnings attach to the node, so they appear on every result of the formula, the curves and the scalars alike. The clean-stall warnings of `m_max,level` are forwarded with its answer. The warnings of the iterates of the root searches are not forwarded (as in `max-level-speed`).

**Implementation remark (#1420, new text) — within the node.** One stall solve per mass and configuration is made and reused (the current mass, the iterates and the roots meet the curves at the same masses). The bisection of the edge of the data stops at `mass_envelope_edge_tolerance` of the mass, a value of its own: `powered_root_tolerance` is a force residual relative to the weight.

**Implementation remark (#1420) — what closes the bracket.** The scan goes up from the current mass. At a mass above the current one, two outcomes mean "the data end" and close the bracket without a sign change: for `m_max,level` the failure `no_feasible_speed` (no speed inside the propeller table at which the wing carries the weight), for `m_max,TO` the failure `outside_propeller_table` (the lift-off speed is beyond the table). The edge between the last mass that evaluates and the first that does not is bisected to `mass_envelope_edge_tolerance` of the mass, the last mass that evaluates is the answer, and the notice `powered_limit_declared` with `limit = evaluation_edge` says so (ADR 0020). Every other failure (a stall solve that does not converge, a stall off the main lift peak, a missing input, any failure at the current mass) is not "not held": it surfaces with the mass of the scan in the message and in `detail.mass_kg`.

**Implementation remark (#1420) — warnings, assumptions.** Warnings forwarded: those of the answer's level-flight point at `m_max,level` (flap, Reynolds, Mach and the drag notice of the adapter), those of the stall solve and the level-flight point of the answer at `m_max,TO` (with the flap-validity declaration), the route notice once, the skipped speeds of the level answer, and `powered_limit_declared` where the best excess lies at the stall corner; the warnings of the iterates are not forwarded. Assumptions: `G(m)` and `T − D` at `V_TO(m)` fall with the mass and cross zero once (bracketed by the upward scan); the best excess has one maximum over the speed (golden section). A state still held at the last mass of the scan (`mass_envelope_max_steps`) is `not_converged`.

**Measured (gh-1420, Avistar Elite 3.70 kg, marked test motor values):** `m_max,level` 17.82 kg, `m_max,TO` 17.82 kg (5 g below); `climb-rate-over-mass` 9.20, 5.17, 3.25, 2.05, 1.19, 0.54 m/s at 3.70, 6.05, 8.41, 10.76, 13.12, 15.47 kg and 0 at 17.82 kg, each sample equal to `max-rate-of-climb` at that mass; the whole run 204 s, a sample about 25 s (climb search about 20 to 27 s, level-speed search and stall solve about 3.5 s). A stall solve of `stall-speed` fails for masses from 8.8 to 9.4 kg on this aircraft (#1423), which the sweep inherits.

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
