---
name: prop-torque-demand
symbol: Q_prop
kind: quantity
unit: Nm
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Propeller absorbed torque

**Definition.** Torque the propeller absorbs at a given shaft RPM and airspeed — the load side of the QPROP torque balance.

**Formula — as the code writes it.**

```
p_prop = cp * rho * (n_rps**3) * (D_m**5) ; omega = 2.0 * math.pi * n_rps ; return p_prop / omega
```

**Inputs.** [[polar-cp|Propeller power coefficient]] · [[air-density-perf|Air density at altitude (performance)]]

**Produced by.** `app/services/powertrain_performance.py:471` — `_prop_torque_demand`

**Consumed by.**

- in this graph: [[qprop-residual|Torque-balance residual]]
- outside it: `app/services/powertrain_performance.py:536`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7 (C_P definition) combined with Sadraey (2013) §8.7, Eq. 8.11 (omega = 2*pi*n/60). Drela, 'DC Motor / Propeller Matching' §1.1 identifies the propeller torque demand Q(n) as the load side of the motor-propeller torque balance.
>
> — via `rc-aircraft-designer / aircraft-design-scholz`

**The source states it as.**

```
Q_prop = P_prop / omega = C_P rho n^3 D^5 / (2 pi n)
```

**Cited in the code itself.** `docstring: "Q_prop = P_prop / ω = Cp·ρ·n³·D⁵ / (2π·n) = Cp·ρ·n²·D⁵ / (2π)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
