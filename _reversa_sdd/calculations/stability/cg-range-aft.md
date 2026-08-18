---
name: cg-range-aft
symbol: x_cg_aft
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Aft CG limit from margin bounds

**Definition.** Most-aft (least stable) CG position, derived from the neutral point and the minimum allowed static margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
aft = np_x - (min_margin / 100) * mac
```

**Inputs.**

- [[neutral-point-x-solver|Neutral point (solver)]]
- [[mac-solver-cref|MAC (solver reference chord)]]
- [[min-static-margin-pct-default|Minimum static margin (CG-range default)]]  — *⤵ fallback*

**Produced by.** `app/services/stability_service.py:98` — `compute_cg_range`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/stability_service.py:334,352` · `app/services/copilot_tools.py:464` · `frontend/components/workbench/MarkerDetailBox.tsx:89 (component never mounted)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2, Eq. 11.18 rearranged, with the aft bound set by Eq. 11.22 (cg must stay forward of the neutral point). Minimum-margin value 5 %: Lennon Ch. 6.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
x_cg,aft = x_np − SM_min · C̄
```

**⚠️ Anomaly.** Duplicates loading_scenario_service's cg_stability_aft_m = x_np - target_sm * mac (loading_scenario_service.py:112) with a different margin source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Aft limit     = NP_x − (min_margin / 100) × MAC  (least stable)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
