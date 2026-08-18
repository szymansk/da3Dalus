---
name: request-altitude-m
symbol: altitude_m
kind: parameter
unit: m
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Operating altitude (performance)

**Definition.** Altitude used for the density correction of the whole velocity sweep.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:222` — `PowertrainPerformanceRequest.altitude_m`

**Consumed by.**

- in this graph: `Air density at altitude (performance)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:695` · `app/services/powertrain_performance.py:721`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eq. 4.51: P_alt = P_SL * sigma with sigma = rho/rho_o — engine and aerodynamic performance both require the altitude density ratio; §8.8.1 Eq. 8.16 P_max = P_max,SL (rho/rho_o)^m gives the power lapse.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
sigma = rho/rho_o ;  P_alt = P_SL sigma  (Eq. 4.51)
```

**⚠️ Divergence from the source.** Sadraey applies the density ratio to BOTH the aerodynamics and the engine power (Eq. 8.16, m = 0.9 piston / 1.2 turboprop). The code applies the altitude correction only to the aerodynamic side; the electrical power ceiling is altitude-independent. For an electric motor that is arguably correct (no air-breathing lapse), but no source in the vaults states that for electric propulsion.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
