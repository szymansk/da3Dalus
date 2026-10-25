---
canon: load-factor
kind: quantity
symbol: "n"
unit: 1
role: input
tags:
  - canon/quantity
  - module/operating-point
  - role/input
type: scalar
data: default:load-factor
---

# Load factor · `n`

Ratio of lift to weight. An **input of the lift balance**, bound per application: 1 in straight level flight, `n_lim` for the envelope. In the sustained turn it is an optimisation variable, not this input. Until 2026-10-01 it was produced from a bank angle (`turn-load-factor`, deleted). The named straight-flight conditions (`stall-speed` clean/take-off/landing, `minimum-drag-speed-from-polar`, `minimum-sink-speed-from-polar`) bind `n = 1` as a constant, the inverted stall `n = −1`; as the generic input at the caller's operating point (default 1, #1181) it is read by [[lift-coefficient-required]], [[control-surface-hinge-moments]] and [[spanwise-loads]].

**Unit.** `1`

**Used by.** [[control-surface-hinge-moments]] · [[lift-coefficient-required]] · [[spanwise-loads]]
