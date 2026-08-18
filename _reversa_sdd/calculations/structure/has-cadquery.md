---
name: has-cadquery
kind: constant
unit: boolean
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
---

# CadQuery availability flag

**Definition.** Whether cadquery is importable on this platform. False raises SectionGeometryUnavailableError, which the services translate into a 422.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Formula — as the code writes it.**

```
_HAS_CADQUERY = importlib.util.find_spec("cadquery") is not None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:54` — `_HAS_CADQUERY`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/section_geometry.py:181` · `app/services/spar_plan_service.py:472` · `app/services/section_thickness.py:140`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (platform capability flag; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `Platform guard: ``cadquery`` is excluded on ``linux/aarch64``. Both modes need it (analytic for ``Plane`` math, solid for the loft); a clear :class:`SectionGeometryUnavailableError` is raised when it is unavailable, so callers can return a 503/422 rather than crashing.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
