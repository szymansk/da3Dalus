---
name: g-default-ss-dead
symbol: G_DEFAULT
kind: constant
unit: m/s^2
cluster: powertrain
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/powertrain
  - class/physical-constant
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/physical
---

# Gravity default (solution space)

**Definition.** Module-level standard gravity, annotated as overridable via assumptions.g.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: gravity.*

**Value.** `9.80665`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:64` — `G_DEFAULT`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> No expert vault attributes the value; 9.80665 m/s^2 is the standard acceleration of free fall fixed by the 3rd CGPM (1901). Sadraey (2013) §4.6 uses g only implicitly through W = m g in C_L = 2W/(rho V^2 S).
>
> — via `aircraft-design-scholz`

**⚠️ Anomaly.** DEAD CONSTANT — grep across app/ finds only this definition. The value actually used is the independent literal 9.80665 at app/schemas/powertrain_solution_space.py:99. Two declarations, one unreachable (ADR 0021/0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# m/s²  (overridable via assumptions.g)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
