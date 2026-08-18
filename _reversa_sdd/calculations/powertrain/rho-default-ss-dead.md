---
name: rho-default-ss-dead
symbol: RHO_DEFAULT
kind: constant
unit: kg/m^3
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/powertrain
  - class/physical-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/physical
---

# Air density default (solution space)

**Definition.** Module-level ISA sea-level density, annotated as overridable via assumptions.rho.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:65` — `RHO_DEFAULT`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6 Eq. 4.51 (sigma = rho/rho_o) and §8.8.1 Example 8.3 ((0.653/1.225)^1.2): rho_o = 1.225 kg/m^3 ISA sea level.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
rho_o = 1.225 kg/m^3
```

**⚠️ Anomaly.** DEAD CONSTANT — same pattern as G_DEFAULT; the operative value is the separate literal at app/schemas/powertrain_solution_space.py:94.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# kg/m³ (ISA sea-level, overridable via assumptions.rho)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
