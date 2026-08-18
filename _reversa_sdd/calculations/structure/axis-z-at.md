---
name: axis-z-at
symbol: axis_z
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - audit/confirmed
---

# Straight-piece axis height at a station

**Definition.** Height of a straight spar piece's axis at an interior station — linear interpolation between its root and tip station center_z, NOT the station's own center_z (the piece cannot follow per-station jitter).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
root, tip = run[0], run[-1]
span = tip.y_mm - root.y_mm
if abs(span) < 1e-9:
    return root.center_z
t = (station.y_mm - root.y_mm) / span
return root.center_z + t * (tip.center_z - root.center_z)
```

**Inputs.**

- [[station-center-z|Station centre height]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:271` — `_axis_z_at`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Largest containable OD for a run`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:278` · `cad_designer/airplane/geometry/spar_solver.py:291`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary linear interpolation. Nearest attributable context: RC-Network Wiki, "Steckung", https://wiki.rc-network.de/wiki/Steckung — a spar joint is "positionally fixed in at least two spatial directions" with the insertion direction free, i.e. a piece is a straight member and cannot follow per-station geometry.
>
> — via `rc-aircraft-designer`

**Cited in the code itself.** `A piece is a single straight line from its root station's ``center_z`` to its tip station's ``center_z`` (by ``y_mm``). The axis z at an interior station is the linear interpolation along that line — NOT the station's own ``center_z`` (the piece cannot follow per-station jitter; it is straight).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
