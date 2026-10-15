---
canon: touchdown-speed-margin-target
kind: quantity
symbol: k_S,TD
unit: 1
role: target
status: draft
tags:
  - canon/quantity
  - role/target
type: scalar
positive: true
default: {value: 1.2, source: "Lennon, Basics of R/C Model Aircraft Design, Ch. 4 and Ch. 14 (20 % safety margin)"}
---

# Touchdown-speed margin target · `k_S,TD`

The margin over the stall speed the touchdown speed is flown at: `V_TD = k_S,TD · V_S0` ([[touchdown-speed]]). A design
target, set by the designer; the default is the sourced value (maintainer, 2026-10-14).

**Unit.** `1`

**Used by.** [[speed-from-stall-margin]]
