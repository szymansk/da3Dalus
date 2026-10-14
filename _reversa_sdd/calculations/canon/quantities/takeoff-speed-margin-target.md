---
canon: takeoff-speed-margin-target
kind: quantity
symbol: k_S,TO
unit: 1
role: target
status: draft
tags:
  - canon/quantity
  - role/target
type: scalar
default: {value: 1.1, source: "Sadraey, Aircraft Design (2013), §4.3.4, V_R ≈ 1.1 V_s"}
---

# Take-off-speed margin target · `k_S,TO`

The margin over the stall speed the take-off speed is flown at: `V_TO = k_S,TO · V_S,TO` ([[takeoff-speed]]). A design
target, set by the designer; the default is the sourced value (maintainer, 2026-10-14).

**Unit.** `1`

**Used by.** [[speed-from-stall-margin]]
