---
name: mkpi_field_friendliness
symbol: field_friendliness
kind: quantity
unit: m
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/wrong-line
  - flag/scale
---

# KPI: field friendliness

**Definition.** Composite take-off plus landing field-length axis.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
formula = "max(s_TO_50ft, s_LDG_50ft); score = target / effective"
```

**Inputs.**

- [[mkpi_effective_field_length|Effective field length]]
- [[mkpi_field_score|Field-friendliness score]]

**Produced by.** `app/services/mission_kpi_service.py:339` — `_kpi_field_friendliness`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `340`. 

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟡 PARTIAL

> Composite of mkpi_effective_field_length (FAR 23.53 obstacle, GA basis) and the unsourced mkpi_field_score ratio.
>
> — via `scholz`

**⚠️ Scale (ADR 0023).** Inherits the 50 ft obstacle scale problem.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
