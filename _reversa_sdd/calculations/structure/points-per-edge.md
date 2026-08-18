---
name: points-per-edge
kind: constant
unit: count
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Slice outline sampling density

**Definition.** Number of points sampled per outline edge when discretising a section cut, clamped to [8, 4096]. Solid mode only.

**Value.** `80 (clamped 8..4096)`

**Formula — as the code writes it.**

```
self._points_per_edge = max(8, min(int(points_per_edge), 4096))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:191` — `SectionGeometry.__init__`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/section_geometry.py:279` · `cad_designer/airplane/geometry/section_geometry.py:280`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (mesh/discretisation density, and unreachable from the spar cluster since both spar paths construct SectionGeometry with the default mode='analytic')`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Three undocumented magic numbers (80, 8, 4096) with no rationale. Unreachable from the spar cluster: both spar paths construct SectionGeometry with the default mode='analytic' (app/services/spar_plan_service.py:471, app/services/section_thickness.py:139), and this value is used only on the solid-slice path.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
