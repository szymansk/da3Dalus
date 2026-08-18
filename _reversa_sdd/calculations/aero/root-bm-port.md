---
name: root-bm-port
kind: quantity
unit: N·m
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Port root bending moment

**Definition.** Root bending moment on the port half.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
root_bending_moment_Nm_port: float = Field(..., description="Root bending moment on the port half (N·m)")
```

**Inputs.**

- [[spanwise-bending-moment|Running bending moment]]

**Produced by.** `app/schemas/spanwise_loads.py:65` — `SurfaceSpanwiseLoads.root_bending_moment_Nm_port`

**Consumed by.**

- in this graph: `Design half-span selection`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_surface_to_stations:2206`

**Source.** 🟢 SOURCED

> Scholz 07_WingDesign §7.4; RC-Network Wiki 'Holm'
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
as root-bm-starboard, for the mirrored half
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
