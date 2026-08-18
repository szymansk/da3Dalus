---
name: hyperbola-c-rate-samples
symbol: c_rate_curve
kind: quantity
unit: 1/h (C)
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Hyperbola C-rate samples

**Definition.** Minimum C-rate at each sampled capacity — the current-constraint boundary of the feasible region.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
c_rates = [i_peak / (c / 1000.0) for c in caps]
```

**Inputs.**

- [[ss-i-peak|Peak battery current]]
- [[hyperbola-capacity-samples|Hyperbola capacity samples]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:183` — `_build_hyperbola`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:471` · `frontend/components/workbench/PowertrainTab.tsx:150` · `frontend/components/workbench/PowertrainTab.tsx:260`

**Source.** 🟡 PARTIAL

> C-rate as I/capacity_Ah is standard battery terminology (see ss-raw-c); no expert vault states it in a citable section.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
C = I_peak / capacity_Ah
```

**⚠️ Divergence from the source.** The plotted boundary omits the c_margin that the recommended C_min includes, so chart and recommendation differ by exactly 1.25 — but since c_margin itself is unattributed, neither curve has a source for its position.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Computed WITHOUT c_margin while the c_min the user is told to shop for INCLUDES c_margin (line 146) — the plotted boundary sits 25 % below the recommended value, so a point can look feasible on the chart and fail the shopping spec.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `schema: "A hyperbolic curve C ≥ i_peak_a / (capacity_mah / 1000) (current constraint)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
