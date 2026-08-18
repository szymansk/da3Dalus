---
name: rho-sea-level-perf
symbol: RHO_SEA_LEVEL
kind: constant
unit: kg/m^3
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: physical-constant
tags:
  - cluster/powertrain
  - class/physical-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/physical
---

# Sea-level air density (performance module)

**Definition.** ISA sea-level air density used as the base of the exponential atmosphere in the performance module.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:48` — `RHO_SEA_LEVEL`

**Consumed by.**

- in this graph: `Air density at altitude (performance)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:348`

**Source.** 🟢 SOURCED

> Sadraey, M., Aircraft Design: A Systems Engineering Approach (Wiley 2013), §4.6, Eq. 4.51 (sigma = rho/rho_o) and worked Example 8.3 in §8.8.1, which evaluates (0.653/1.225)^1.2 — rho_o = 1.225 kg/m^3 is the ISA sea-level reference density
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
sigma = rho / rho_o,  rho_o = 1.225 kg/m^3 (ISA sea level)
```

**⚠️ Anomaly.** Fourth independent literal of 1.225 in the cluster (see notes F2); endurance_service.py:50, powertrain_solution_space_service.py:65 and app/schemas/powertrain_solution_space.py:93 each declare their own.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# kg/m³`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
