---
canon: advance-ratio
kind: quantity
symbol: J
unit: 1
role: derived
status: draft
tags:
  - canon/quantity
  - role/derived
type: scalar
---

# Advance ratio · `J`

How far the propeller advances per revolution, relative to its diameter: `J = V/(n·D)`.
The axis the measured propeller tables are indexed by, and the reason thrust falls with
airspeed — as `J` rises the blade's angle of attack drops and the thrust coefficient slides
toward zero.

Produced by [[advance-ratio-from-speed]] because
it is never computed for its own sake.

**Unit.** `1`

**Produced by.** [[advance-ratio-from-speed]]

**Used by.** [[propeller-table-lookup]]
