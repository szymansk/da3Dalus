---
name: spanwise-y-m
symbol: y
kind: quantity
unit: m
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Strip spanwise station

**Definition.** Absolute distance from the wing root to the strip centre, positive for both halves.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y_m: float = Field(...)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spanwise_loads.py:19` — `SpanwiseLoadEntry.y_m`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Running bending moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_surface_to_stations` · `_get_tc_by_y_for_surface` · `frontend/hooks/useSpanwiseLoads.ts` · `frontend/lib/sparPlanHelpers.ts`

**Source.** 🟢 SOURCED

> Scholz 07_WingDesign §7.1 and §7.3; Sadraey §5.8 (lift distribution vs normalised spanwise position)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
eta = 2y/b, y measured from the plane of symmetry, y ∈ [−b/2, +b/2]
```

**⚠️ Divergence from the source.** MATERIAL sign convention departure: both sources use SIGNED y from the plane of symmetry (port negative). The code stores \|y\| for port entries, so a port station and its starboard mirror are indistinguishable by value. Any consumer that reconstructs geometry (sparPlanHelpers, section-thickness lookup) must re-apply the sign externally.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Port entries store \|y\| while the physical Yle is negative — the schema documents the sign flip but the value silently contradicts the coordinate system.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
