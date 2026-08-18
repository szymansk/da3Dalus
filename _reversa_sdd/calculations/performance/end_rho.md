---
name: end_rho
symbol: rho_0
kind: constant
unit: kg/m^3
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/perf-envelope
  - class/physical-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/scale
  - flag/physical
---

# Sea-level air density

**Definition.** ISA sea-level density; endurance is evaluated only at sea level.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Formula — as the code writes it.**

```
RHO_SEA_LEVEL = 1.225  # kg/m³
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:50` — `RHO_SEA_LEVEL`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Speed-specific C_D0` · `Dynamic pressure (endurance)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `powertrain_sizing_service.AIR_DENSITY_SEA_LEVEL`

**Source.** 🟢 SOURCED

> ISO 2533:1975 ISA sea level; ICAO Doc 7488.
>
> — via `scholz`

**The source states it as.**

```
rho_0 = 1.225 kg/m^3
```

**⚠️ Scale (ADR 0023).** No altitude parameter exists in the service, so endurance and range are sea-level-only. Not stated in the API description — a user flying from a 1500 m field gets a silently optimistic number.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** No altitude parameter anywhere in the service — endurance and range are always sea-level values, which is not stated in the API description.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
