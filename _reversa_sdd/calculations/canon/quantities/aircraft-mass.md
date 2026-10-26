---
canon: aircraft-mass
kind: quantity
symbol: m
unit: kg
role: input
tags:
  - canon/quantity
  - module/mass-and-balance
  - role/input
type: scalar
data: app:AssumptionRead.effective_value
consistency: geometry:total_mass_kg

positive: true
---

# Aircraft design mass · `m`

Take-off mass of the aircraft. **An explicit input of every analysis** (maintainer, 2026-10-26, #1302: "Es ist besser, die Masse immer vorgeben zu müssen bei einer Analyse, als sie implizit aus dem Flugzeug zu lesen"). Its data source is the app's effective design mass: the design assumption `mass` (`AssumptionRead.effective_value`), calculated from the component tree — the authority, ADR 0022 — or overridden by the designer, passed as `values["aircraft-mass"]`. **No default**: a request that needs `m` without a supplied value is `missing_input`; its hint names the geometry file's `total_mass_kg` where the file states one ("pass it explicitly to use it"), but the kernel never reads it as the mass. `geometry:total_mass_kg` stays a secondary statement of the geometry format, a **consistency check only**: the kernel warns (`conflicting_mass`) when it differs from the passed mass.

**Unit.** `kg`

**Used by.** [[aileron-deflection-required]] · [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[butterfly-approach]] · [[control-surface-hinge-moments]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[lateral-static-stability-app]] · [[lateral-static-stability-md]] · [[lift-coefficient-required]] · [[maneuvering-speed]] · [[mass-envelope]] · [[max-level-speed]] · [[max-mass-structure]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[minimum-drag-speed-from-polar]] · [[minimum-sink-speed-from-polar]] · [[motor-propeller-part-load]] · [[neutral-point]] · [[parabolic-polar-fit]] · [[roll-rate]] · [[roll-rate-cruise-target]] · [[spanwise-loads]] · [[spar-break-load-factor]] · [[spiral-parameter]] · [[stall-speed]] · [[static-margin-probe]] · [[weight-from-mass]] · [[wing-loading]]
