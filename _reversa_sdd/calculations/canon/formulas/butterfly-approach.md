---
canon: butterfly-approach
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: butterfly-stall-speed-curve, butterfly-approach-speed-curve, butterfly-glide-angle-curve, butterfly-max-mix
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}V_{S0}(s) &= \min_{V,\,\alpha} V \;\;\text{u.d.N.}\;\; L(V,\alpha;\,s) = m\,g \\ V_{app}(s) &= V_{app}\,\frac{V_{S0}(s)}{V_{S0}(0)} \\ s_{max}&:\; V_{S0}(s_{max}) = V_{app}\end{aligned}
inputs:
  airplane: null
  m: aircraft-mass
  g: gravity
  n_load: null
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  v_app: approach-speed
  delta_f_ldg: flap-deflection-landing
  delta_f_crow: crow-flap-deflection
  delta_a_crow: crow-aileron-deflection
outputs:
  v_s0_curve: butterfly-stall-speed-curve
  v_app_curve: butterfly-approach-speed-curve
  gamma_curve: butterfly-glide-angle-curve
  s_max: butterfly-max-mix
applications:
  - id: crow
    bind: {airplane: airplane-landing, n_load: {const: 1, source: "definition of the load factor n = L/W (as stated in max-mass-structure); straight level flight means L = W"}}
    when: has_separate_flap_and_aileron
preconditions:
  - {id: approach_speed_positive, parameter: v_app, on_violation: error}
  - {id: crow_aileron_not_negative, parameter: delta_a_crow, on_violation: error}
postconditions:
  - {id: optimum_at_main_cl_peak, parameter: v_s0_curve, on_violation: error}
---

# Butterfly (crow) in the approach — how far it may be mixed in

**Canonical form**

```
for the crow mix s in [0, 1], starting from the landing configuration (s = 0):
  delta_f(s) = delta_f,landing + s * (delta_f,crow - delta_f,landing)      flaps down
  delta_a(s) = s * delta_a,crow                                           ailerons up
  minimize over V, alpha:  V      subject to:  L(V, alpha; s) = m * g        ->  V_S0(s)
  V_app(s)  = V_app * V_S0(s) / V_S0(0)              (same reserve k_S as without crow; V_S0(0) from this sweep)
  gamma(s)  = glide angle at V_app(s), configuration s
  s_max     : V_S0(s_max) = V_app                    (stall reaches the approach speed flown without crow)
```

**Produces** [[butterfly-stall-speed-curve]] · [[butterfly-approach-speed-curve]] · [[butterfly-glide-angle-curve]] · [[butterfly-max-mix]]  ·  **from** [[airplane-landing]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[approach-speed]] · [[flap-deflection-landing]] · [[crow-flap-deflection]] · [[crow-aileron-deflection]]

**Base configuration (maintainer, 2026-10-15, E2).** `s = 0` is the landing configuration
([[airplane-landing]]); the crow angles are absolute end deflections: the flaps run from
`δ_f,landing` to `δ_f,crow`, the ailerons from 0 to `δ_a,crow` (up). `V_app(s)` is normalised with
`V_S0(0)` of the same sweep, so clean and landing stall speeds are not mixed.

**Kind: an optimisation problem** — the [[stall-speed]] problem with the airplane in crow
configuration, swept over the mix `s`. The core is the curve `V_S0(s)`; two readings follow
from it (maintainer, 2026-10-02):

- **a) the pilot adapts the speed:** `V_app(s)` and the glide angle `gamma(s)` — *"with half
  crow, fly the approach at X m/s and come down at Y°"*. No stall risk by construction: the
  reserve `k_S` is kept.
- **b) the pilot holds the speed and mixes in on short final** — the typical case and the
  original question: `s_max`, the largest mix at which the stall speed has not yet reached
  the approach speed flown without crow. Between `s = 0` and `s_max` the reserve shrinks from
  `k_S` to 1; the curve shows it. If `V_S0(s)` does not reach `V_app` up to `s = 1` — because it
  does not rise with `s` (the raised ailerons can delay the outboard stall), or rises without
  reaching the approach speed — there is no `s_max`: *"fully mixable"*.

**Exists only if the geometry has camber flaps and ailerons** (as A3 for the flap
configurations): crow needs both.

**The stall optimum at every `s` lies at the main `C_L` peak** (the local maximum above α = 0 with the largest fall behind it, [[stall-speed]]; maintainer 2026-11-27, #1423) — postcondition
`optimum_at_main_cl_peak`, checked at every s; same check as stall-speed (K32), one shared
implementation, not a copy (architect, 2026-10-15). Not an embed: a form that re-solves another
formula's problem under a configuration it varies itself is not an embed (ARCHITECTURE §8.5).

**Declared limit — approval needs a comparison.** Crow flaps deflect 45–80°; RC practice goes up to 90°. The flow on the flap is separated there, and the section method does not know it. *Correction by evidence (#1402; the earlier text of this paragraph described the `τ·δ` angle shift, which since #1212 is the model of the roll aileron only):* the kernel evaluates the lowered flap **and the raised aileron** as the **deflected contour** — the airfoil behind the hinge rotated by the angle (trailing edge down positive; a raised aileron is a negative angle), handed to NeuralFoil inside AeroBuildup, the same as the flap of [[airplane-configuration]] (`aero_kernel/devices.py: crow_configuration`; the raised aileron is carried as a symmetric flap-like contour for the tools). There is no flap separation model. What the kernel declares, per [[airplane-configuration]], with the rule `flap-model-validity`: `flap_deflection_beyond_validity` for any deflected device above 30° (by magnitude), and `flap_confidence_low` where NeuralFoil's area-weighted `analysis_confidence` over the span of the device is below 0.85; both are evaluated **at the mix of the sweep with the largest deflection** (full crow unless the crow flap angle is below the landing flap angle), and the value is still computed. Measured on the RV-7 section (NACA 23013.5, hinge 0.75 c, section `C_l,max`, NeuralFoil xlarge, evidence sheet of `butterfly-approach`): at Re 1·10⁵ the confidence at the stall is 0.97 clean, 0.96 at 15°, 0.52 at 30°, 0.01 at 45° and 0.00 from 60° to 90°; a raised aileron gives 0.70 at 20° up and 0.05 at 40° up. Above about 30° the numbers of this formula are therefore **not a prediction**, whatever their precision; they are what the section method returns. Approval requires a check against measured or plan values of a glider in the reference fleet; the fleet has no glider with separate flaps and ailerons and no crow measurement (evidence sheet), so that comparison does not exist yet. *Also declared (#1402):* a sweep whose stall solve fails at one mix fails the whole formula, no curve with a hole is returned. On the RV-7 (landing flap 30°) a crow of 45° flap and 15° aileron up converges at all eleven mixes (`V_S0` 6.250 to 6.835 m/s), whereas 60° and 20° up fails at `s = 0.8`: the stall optimum lies on the angle-of-attack bound at 11.0°, and the first `C_L` peak jumps from 11.6° at `s = 0.7` to 16° at `s = 0.9`.

**Source.** 🟡 PARTIAL — the stall relation as in [[stall-speed]]; crow as the dominant landing
aid for models per the RC sources (§3.7); the reading of the question is the maintainer's.

**Validity in the RC/UAV regime (ADR 0028).** The stall relation is the one in [[stall-speed]] and inherits its Reynolds-number qualification. Crow is RC practice: flaps down (up to 90°) and ailerons up, the inner-wing lift gain partly cancelled by the outer-wing loss, needing slightly higher approach speeds than a minimum-speed landing (RC-Network wiki, *Landehilfen*); its braking comes mainly from the strongly non-elliptic loading and the induced drag that follows (*Butterfly*); since RC practice deflects crow flaps up to 90°, the declared limit above applies up to 90°, not only to 45–80°. AeroBuildup computes induced drag at aircraft level through a Trefftz-plane projection (Sharpe 2024 §5.3), so that mechanism is represented as far as the section lifts are right. The section lifts are where it fails: at 45–80° the flap is far outside the attached range where linear estimates hold (Anderson §4.13), and below chord Re 7·10⁴ laminar separation sets in even undeflected (§20.3.2). *Correction by evidence (#1402):* NeuralFoil was not trained on contours with such a flap (its confidence is 0 from 60°, see the declared limit); both the lowered flap and the raised aileron are evaluated as deflected contours, with no separation, so the sign and size of the net error in `V_S0(s)`, and hence in `s_max`, are open [no source]. Mach ≤ 0.3 needs no correction (Anderson §1.10.3).

## Implementation notes (#1402)

*Not dated maintainer decisions; what the implementation does where the entry was silent.*

- **The mix grid.** `s` runs from 0 to 1 in `butterfly_mix_steps` equal steps (`config.yaml`, 10: eleven samples); each sample is one stall solve ([[stall-speed]]'s problem, `n = 1`, `L = m g`) on the airplane in the configuration `crow_configuration(s)`. `s_max` is the first crossing of `V_S0(s)` with `V_app`, interpolated linearly between the two samples that bracket it (`V_S0(s)` is convex in `s` for a linear `C_L,max(s)`, so the interpolated mix is slightly below the root; on the RV-7 an independent real stall at the interpolated mix lands within 1 % of the approach speed, see the evidence). `V_S0(0) ≥ V_app` gives `s_max = 0`.
- **Devices, by role.** Flaps: the devices of role `flap` run from `δ_f,landing` to `δ_f,crow`. Ailerons: the devices of role `aileron` or `elevon` rise from 0 to `δ_a,crow`. A flaperon is neither (D10): it keeps the angle the landing configuration gave it. `crow-aileron-deflection` is **the angle the aileron is raised**, a positive number of degrees up; a negative value is refused (`invalid_input`).
- **The glide angle** is the steady glide without thrust, `γ = atan(C_D/C_L)` with `L = m g`, read at `V_app(s)` from the one lift-equals-weight solve of the kernel (`OptiAdapter.level_flight_point`, shared with the level-flight polar and the powertrain: the angle on the pre-stall branch where AeroBuildup's lift is `m g`, by secant steps to the configured tolerance; `γ = atan2(C_D, C_L)` in the formula; the drag is the kernel's, [[aerobuildup-evaluation]]). A `V_app(s)` below the stall speed of the configuration (an approach margin below 1) is `not_converged`.
- **The curves** are values inside the node (`Curve`, `StallCurve`); they are requestable as curve results (gh-1424): `x` the mix `s`, `y` the quantity in its unit (the stall curve returns its `x`, `y` only). `butterfly-max-mix` is the carried scalar.
- **No largest mix (interim, Soll: #1402).** The kernel has no declared absent output, so a stall speed that never reaches `V_app` up to `s = 1` is an `error` of `butterfly-max-mix` whose `detail` carries the sweep (ARCHITECTURE Q39). The maintainer decides whether an absent output becomes a `not_applicable` result with its own reason (shared with `airplane-components`) or stays this declared error; until then "fully mixable", the ordinary result with a normal approach margin, is an error.
- **Validity declarations** are read at the mix with the largest deflection only (one warning per device, not one per sample).
- **Caveats forwarded.** The adapters report caveats per solve; the formula forwards the caveats of the two solves the answer rests on (the landing stall at `s = 0` and the sample that closes the bracket of `s_max`, full crow where there is no crossing) with the glide read at the same mixes, plus one `control_surface_fit_range_unknown` carrying, per device, the largest deflection and the lowest NeuralFoil confidence over the whole sweep. The regime and drag messages of the other mixes are dropped (they repeat with another Reynolds number); the answer's own Reynolds regime is that of the forwarded solves.
- **The stall problem is level** (`n = 1`, bound with its source in the application, as in [[stall-speed]]); the preconditions `approach_speed_positive` and `crow_aileron_not_negative` refuse a non-positive approach speed and a negative crow aileron angle before any solve.
- **`V_app` at or below `V_S0(0)`.** `s_max = 0` and the glide-angle curve is empty: no glide exists below the stall speed, none is read.
- **The main-peak check also guards the no-crossing path:** a mix on another branch is the error that names it, not "fully mixable".
- **The check** `optimum_at_main_cl_peak` runs on the sweep of every mix (shared function with `stall-speed`); a violation names the mix in `detail`.

## Implementations (1)

[[butterfly-approach]] is implemented in `aero_kernel/formulas/butterfly_approach.py`; no app implementation maps to this entry.

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
