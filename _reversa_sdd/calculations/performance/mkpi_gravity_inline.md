---
name: mkpi_gravity_inline
symbol: g
kind: constant
unit: m/s^2
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/perf-envelope
  - class/physical-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Gravity (mission KPI, inline)

**Definition.** Gravity literal embedded directly in the wing-loading expression.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: gravity.*

**Value.** `9.81`

**Formula — as the code writes it.**

```
value = mass_kg * 9.81 / s_ref
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:273` — `_kpi_wing_loading`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `KPI: wing loading`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Rounded standard gravity (CGPM 1901 / ISO 80000-3), as fe_gravity.
>
> — via `scholz`

**⚠️ Divergence from the source.** Third gravity in the cluster and the only one that is a bare inline literal — not a named constant and not imported from either existing constant. This is the copy that produces the USER-VISIBLE wing loading.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Bare literal, not a named constant and not imported from either of the two existing gravity constants in this cluster.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
