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
  rho: air-density
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
    bind: {airplane: airplane-landing}
    when: has_separate_flap_and_aileron
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

**Produces** [[butterfly-stall-speed-curve]] · [[butterfly-approach-speed-curve]] · [[butterfly-glide-angle-curve]] · [[butterfly-max-mix]]  ·  **from** [[airplane-landing]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[approach-speed]] · [[flap-deflection-landing]] · [[crow-flap-deflection]] · [[crow-aileron-deflection]]

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
  `k_S` to 1; the curve shows it. If `V_S0(s)` does not rise with `s` — the raised ailerons can
  delay the outboard stall — there is no `s_max`: *"fully mixable"*.

**Exists only if the geometry has camber flaps and ailerons** (as A3 for the flap
configurations): crow needs both.

**Declared limit — approval needs a comparison.** Crow flaps deflect 45–80°; the flow on the
flap is separated there. AeroBuildup has no flap model of its own, and NeuralFoil never sees the deflected surface: AeroSandbox evaluates the clean airfoil at `α_eff = α + τ·δ`, `τ = 1 − x_hinge^2.7514` (a δ-independent fit to an XFoil study), and multiplies the drag by a factor fitted to Hoerner, *Fluid Dynamic Drag*, p. 13-13 Fig. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255`, reached from `aero_buildup.py:784-801`; AeroSandbox 4.2.9 / NeuralFoil 0.3.2). There is no flap separation: the effectiveness is over-predicted at large δ until the clean section stalls, and the δ range of the τ fit is unknown. At crow deflections the flap
effect is therefore over-predicted. Approval requires a check against measured or plan values of a
glider in the reference fleet.

**Source.** 🟡 PARTIAL — the stall relation as in [[stall-speed]]; crow as the dominant landing
aid for models per the RC sources (§3.7); the reading of the question is the maintainer's.
