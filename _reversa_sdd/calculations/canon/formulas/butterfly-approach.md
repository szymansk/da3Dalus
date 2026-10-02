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
tex: \begin{aligned}V_{S0}(s) &= \min_{V,\,\alpha} V \;\;\text{u.d.N.}\;\; L(V,\alpha;\,s) = m\,g \\ V_{app}(s) &= V_{app}\,\frac{V_{S0}(s)}{V_{S0}} \\ s_{max}&:\; V_{S0}(s_{max}) = V_{app}\end{aligned}
---

# Butterfly (crow) in the approach — how far it may be mixed in

**Canonical form**

```
for the crow mix s in [0, 1]  (flaps down, ailerons up, as constructed, scaled by s):
  minimize over V, alpha:  V      subject to:  L(V, alpha; s) = m * g        ->  V_S0(s)
  V_app(s)  = V_app * V_S0(s) / V_S0                 (same reserve k_S as without crow)
  gamma(s)  = glide angle at V_app(s), configuration s
  s_max     : V_S0(s_max) = V_app                    (stall reaches the approach speed flown without crow)
```

**Produces** [[butterfly-stall-speed-curve]] · [[butterfly-approach-speed-curve]] · [[butterfly-glide-angle-curve]] · [[butterfly-max-mix]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[stall-speed-landing]] · [[approach-speed]]

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
flap is separated there. NeuralFoil's flap model, on which AeroBuildup builds, is not made for
such deflections — the result is reliable for moderate flap angles (up to about 20–30°), not
yet for true landing settings. Approval requires a check against measured or plan values of a
glider in the reference fleet.

**Source.** 🟡 PARTIAL — the stall relation as in [[stall-speed]]; crow as the dominant landing
aid for models per the RC sources (§3.7); the reading of the question is the maintainer's.
