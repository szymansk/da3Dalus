---
name: end_cd_total
symbol: C_D
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/scale
---

# Total drag coefficient

**Definition.** Parabolic-polar drag coefficient at the evaluation speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd = cd0 + k * cl * cl
```

**Inputs.**

- [[end_cd0_at_v|Speed-specific C_D0]]
- [[end_k_induced|Induced-drag factor]]
- [[end_cl|Level-flight lift coefficient]]

**Produced by.** `app/services/endurance_service.py:122` — `_power_required`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Drag force`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e §6.7.2; Scholz 05_PreliminarySizing §5.7. Module's assumption 5 states the validity limit explicitly and correctly.
>
> — via `aero, scholz`

**The source states it as.**

```
C_D = C_D0 + C_L^2/(pi*e*AR)
```

**⚠️ Scale (ADR 0023).** Parabolic polar assumed valid over the whole speed sweep — reasonable for a Class-I estimate, but at RC Reynolds numbers C_D0 itself varies strongly with V. The service already knows this (see end_cd0_at_v) and applies the Re table only at two discrete speeds.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `"Linear polar valid for entire speed sweep (C_D = C_D0 + C_L²/(π·e·AR))" (assumption 5); module header cites "Anderson 6e §6.4–6.5", "Hepperle 2012", "Traub 2011: Range and endurance estimates for battery-powered aircraft"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
