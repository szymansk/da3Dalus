---
canon: tail-efficiency
kind: quantity
symbol: eta_h
unit: 1
role: input
status: draft
tags:
  - canon/quantity
  - module/conventions
  - role/input
type: scalar
positive: true
at_most: 1
---

# Tail efficiency · `eta_h`

The ratio of the dynamic pressure at the horizontal tail to the free-stream dynamic pressure, `eta_h = q_h / q`. A sourced value (default 0.65 after Lennon Ch. 7/8, `defaults.yaml`; basis changed from convention to sourced by the maintainer on 2026-10-25), adopted on 2026-10-24 (#1205); the designer overrides it per airplane: a tail in the wing's wake has less, a T-tail more. Used by the textbook world of [[neutral-point]] only; the Pappas and AVL worlds imply `eta_h = 1`.

**Unit.** `1`  ·  admissible range `0 < eta_h <= 1`

**Used by.** [[neutral-point]]
