---
name: characteristic-points
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Characteristic points dict

**Definition.** Six-key dict bundling max-L/D, CDmin, CLmax, CD0, stall and trim points.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
points = {"maximum_lift_to_drag_ratio_point": None, "minimum_drag_coefficient_point": None, "maximum_lift_coefficient_point": None, "drag_at_zero_lift_point": None, "stall_point": None, "trim_point_cm_equals_zero": None}
```

**Inputs.**

- [[max-ld-point|Maximum L/D point]]
- [[min-cd-point|Minimum drag coefficient point]]
- [[max-cl-point|Maximum lift coefficient point]]  — *⊣ limit*
- [[drag-at-zero-lift-point|Drag at zero lift point]]
- [[stall-point|Stall point]]  — *⊣ limit*
- [[trim-point-cm-zero|Trim point (Cm = 0)]]

**Produced by.** `app/services/analysis_service.py:219` — `_compute_alpha_sweep_characteristic_points`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `analyze_alpha_sweep:714 (API response)` · `get_alpha_sweep_diagram_url` · `copilot_tools._run_polar_async:366` · `MCP analyze_alpha_sweep tool`

**Source.** 🟡 PARTIAL

> Container only; each member is sourced separately (Anderson 6e §6.7.2, §4.3, §4.x; Sadraey §11.6.2).

**⚠️ Divergence from the source.** No source groups these six as a set; the bundle is a project construct.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Present in the /alpha_sweep JSON response but the frontend never reads it — frontend/hooks/useAnalysis.ts:112 extracts only 'analysis' and 'speed_polar'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
