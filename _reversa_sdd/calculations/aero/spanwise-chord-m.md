---
name: spanwise-chord-m
symbol: c(y)
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
---

# Local strip chord

**Definition.** Chord at the strip station.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
chord_m: float = Field(..., description="Local chord at this strip (m)")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spanwise_loads.py:28` — `SpanwiseLoadEntry.chord_m`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Station chord in millimetres`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_surface_to_stations` · `frontend useSpanwiseLoads`

**Source.** 🟢 SOURCED

> Scholz 07_WingDesign §7.1 (Wing Sections and Airfoil Scaling)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
c(y) = c_r · [1 − (1 − lambda)·(y/(b/2))]
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
