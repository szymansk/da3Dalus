---
canon: hinge-moment
kind: quantity
symbol: H
unit: N*m
role: output
status: draft
tags:
  - canon/quantity
  - discipline/structure
  - point/free
  - role/output
type: per_control_surface
---

# Hinge moment of every control surface · `H`

One value per control surface, keyed by `<wing>.<device>[_left|_right]` — the unique wing name, the geometry
device name and, for a mirrored device, the side (e.g. `Seitenleitwerk_links.rudder`; twin fins are
separate devices; no length limit), each at its role's deflection; a dual-role surface carries one value per role, keyed by the
application that produced it (`aileron`, `elevator_up`, `elevator_down`, `rudder`, `flap_takeoff`,
`flap_landing`). At the speed and load factor the caller supplies; pitch untrimmed. Positive is the
aerodynamic moment in the +deflection sense. Inviscid, attached flow: typically an over-estimate in
attached flow, unbounded under separation, at large deflection or below chord Re 7·10⁴ (see
[[control-surface-hinge-moments]]). Not a servo
torque requirement.

**Unit.** `N*m`

**Produced by.** [[control-surface-hinge-moments]]
