---
canon: turn-sideslip-gain
kind: quantity
symbol: kappa
unit: 1
role: output
tags:
  - canon/quantity
  - discipline/lateral
  - point/minimum-sink
  - role/output
type: scalar
---

# Sideslip per unit yaw rate in the turn · `kappa`

`kappa = -C_l_r / C_l_beta`, both derivatives from AVL at the minimum-sink speed: the sideslip angle (rad) that cancels one unit of non-dimensional yaw rate by roll balance. Drela's "approximately 1" up to 3π/8 ≈ 1.18 (elliptic strip theory) is the textbook range; the canon reports the AVL value of the aircraft.

**Unit.** `1` (`1/rad ÷ 1/rad`; the product `kappa·r̂` is an angle in rad).

**Produced by.** [[turn-sideslip]]

**Applies to.** Aircraft without ailerons (`has_no_aileron`).
