---
canon: load-factor
kind: quantity
symbol: "n"
unit: dimensionless
role: input
status: draft
tags:
  - canon/quantity
  - role/input
type: scalar
default: {value: 1, source: "definition of the load factor n = L/W (as stated in max-mass-structure); straight level flight means L = W"}
---

# Load factor · `n`

Ratio of lift to weight. An **input of the lift balance**, bound per application: 1 in straight level flight, `n_lim` for the envelope. In the sustained turn it is an optimisation variable, not this input. Until 2026-10-01 it was produced from a bank angle (`turn-load-factor`, deleted). The named straight-flight conditions (`stall-speed` clean/take-off/landing, `minimum-drag-speed-from-polar`, `minimum-sink-speed-from-polar`) bind `n = 1` as a constant, the inverted stall `n = −1`; only [[lift-coefficient-required]] reads this input, at the caller's operating point, default 1 (#1181).

**Unit.** `dimensionless`

**Used by.** [[lift-coefficient-required]]
