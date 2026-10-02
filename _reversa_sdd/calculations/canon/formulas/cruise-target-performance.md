---
canon: cruise-target-performance
entry: formula
kind: procedure
tool: OPT
shape: law
status: draft
output: endurance-at-cruise-target, range-at-cruise-target
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Endurance and range at the mission's cruise speed

**Canonical form**

```
solve for alpha at V_cruise,target:   L = m * g
t_cruise = 3600 * E_bat * eta / ( D(V_cruise,target) * V_cruise,target )
R_cruise = 3600 * E_bat * eta / D(V_cruise,target)
```

**Produces** [[endurance-at-cruise-target]] · [[range-at-cruise-target]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[propulsive-efficiency]] · [[cruise-speed-target]]

**Kind: a procedure — the solver at a named speed.** At the target speed the level-flight `α` is solved
from `L = m·g` (AeroBuildup), the drag `D` taken from the solver (ADR 0026). Power required is
`P = D·V/η`; endurance `t = 3600·E_bat/P`; range `R = V·t = 3600·η·E_bat/D` — so range is largest
where drag is smallest (`V_md`) and endurance where power is smallest (`V_mp`) (§3.5: two closures,
not three). Both factors of the range come from the **same** speed — the precondition §3.5 named.

**Declared simplifications.** `η` is one number for the whole drive train (`propulsive-efficiency`),
although the propeller's efficiency varies with the advance ratio; the battery is taken as its
usable energy, no voltage sag, no reserve.

**Measured against a target.** A UAV mission often prescribes its cruise speed (area coverage per
time, wind penetration). This entry answers *how long and how far at that speed* — the UAV purpose
names cruise speed explicitly. Not a pilot's choice as a closure (§3.5): the speed is a mission
requirement, the result is measured against it (A9).
