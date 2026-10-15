---
canon: approach-speed-margin-target
kind: quantity
symbol: k_S,app
unit: 1
role: target
status: draft
tags:
  - canon/quantity
  - role/target
type: scalar
positive: true
default: {value: 1.3, source: "Lennon, Basics of R/C Model Aircraft Design, Ch. 20 (FAR 23 reasoning, scaled); CS 25.125 as transport-category reference"}
---

# Approach-speed margin target · `k_S,app`

The margin over the stall speed the approach speed is flown at: `V_app = k_S,app · V_S0` ([[approach-speed]]). A design
target, set by the designer; the default is the sourced value (maintainer, 2026-10-14).

**Unit.** `1`

**Used by.** [[speed-from-stall-margin]]
