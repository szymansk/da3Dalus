---
canon: endurance-and-range
entry: formula
kind: procedure
tool: OPT
shape: law
status: draft
output: max-endurance, max-range
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: t_{max} = \frac{3600\,E_{bat}\,\eta}{D(V_{mp})\,V_{mp}}, \qquad R_{max} = \frac{3600\,E_{bat}\,\eta}{D(V_{md})}
---

# Greatest endurance and greatest range — the two cruise closures

**Canonical form**

```
solve for alpha at V:   L(V, alpha) = m * g          D(V) := D(V, alpha)
t(V) = 3600 * E_bat * eta / ( D(V) * V )        R(V) = 3600 * E_bat * eta / D(V)
t_max = t(V_mp)        R_max = R(V_md)
```

**Produces** [[max-endurance]] · [[max-range]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[propulsive-efficiency]] · [[minimum-sink-speed]] · [[minimum-drag-speed]]

**Kind: a procedure — the solver at a named speed.** At the speed the level-flight `α` is solved
from `L = m·g` (AeroBuildup), the drag `D` taken from the solver (ADR 0026). Power required is
`P = D·V/η`; endurance `t = 3600·E_bat/P`; range `R = V·t = 3600·η·E_bat/D` — so range is largest
where drag is smallest (`V_md`) and endurance where power is smallest (`V_mp`) (§3.5: two closures,
not three). Both factors of the range come from the **same** speed — the precondition §3.5 named.

**Declared simplifications.** `η` is one number for the whole drive train (`propulsive-efficiency`),
although the propeller's efficiency varies with the advance ratio; the battery is taken as its
usable energy, no voltage sag, no reserve.

**Replaces** (2026-10-02, maintainer) `cruise-speed-resolution` (`V_cruise := V_md`, a generic
quantity as output — A2 — and an undeclared substitution — ADR 0020), `power-required-electrical`,
`endurance-from-battery` and `range-from-endurance` (`R = V_cruise · t` with `t` at an unrelated
speed). Both results are **properties of the aircraft**, no target involved.
