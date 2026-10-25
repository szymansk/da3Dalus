---
canon: motor-torque
kind: quantity
symbol: Q_m
unit: N*m
role: output
tags:
  - canon/quantity
  - discipline/powered
  - point/free
  - role/output
type: scalar
---

# Motor shaft torque at the operating point · `Q_m`

The shaft torque at the motor–propeller balance point at the given flight speed:
`Q = C_P(J)·ρ·n_prop²·D_prop⁵/(2π) = P_shaft/(2π·n_prop)` — the torque the propeller absorbs, equal to
the motor torque at the balance on route B; route A below the power limit: upper estimate. An additional output of [[motor-propeller-equilibrium]] (maintainer,
2026-10-19). Which speed the motor mount is designed for (static, `V = 0`, is the usual maximum) and any
factor belong to the construction and the evaluation (A10).

**Unit.** `N*m`

**Produced by.** [[motor-propeller-equilibrium]]
