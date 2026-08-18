---
name: center-z-by-y
kind: quantity
unit: mm
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
---

# Section centre-Z map

**Definition.** Per-station vertical centre of the built section, passed through to spar sizing.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
thickness_by_y, center_z_by_y = build_thickness_maps_for_surface(db=db, aeroplane_id=aeroplane_id, surface_name=surface.surface_name, station_ys_m=station_ys)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2242` — `_get_tc_by_y_for_surface`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `compute_spar_sizing`

**Source.** 🔴 NO SOURCE FOUND

> Geometry pass-through from the built CAD section; no aerodynamic or structural source defines it as a design quantity.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
