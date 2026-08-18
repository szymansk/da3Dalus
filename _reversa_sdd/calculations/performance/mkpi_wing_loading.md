---
name: mkpi_wing_loading
symbol: W/S
kind: quantity
unit: N/m^2
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# KPI: wing loading

**Definition.** Weight per reference wing area.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
value = mass_kg * 9.81 / s_ref
```

**Inputs.**

- [[mkpi_mass|Mass for wing loading]]
- [[mkpi_gravity_inline|Gravity (mission KPI, inline)]]

**Produced by.** `app/services/mission_kpi_service.py:273` — `_kpi_wing_loading`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟢 SOURCED

> Definitional; Scholz 07_WingDesign §7.3 establishes W/S as the governing parameter for gust response and ride quality.
>
> — via `scholz`

**The source states it as.**

```
W/S = m*g/S
```

**⚠️ Divergence from the source.** Third producer of W/S in this cluster (fe:88, fe:135, mkpi:273) and the user-visible one, computed with an inline 9.81 while endurance uses 9.80665. ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third producer of W/S in this cluster (flight_envelope_service lines 88 and 135 compute the same quantity with a different g).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
