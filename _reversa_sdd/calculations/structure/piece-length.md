---
name: piece-length
symbol: L
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
---

# Spar piece length

**Definition.** Straight-line length of a spar piece from its root station point to its tip station point in the wing-local frame.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
length = math.dist(origin, tip_point)
```

**Inputs.**

- [[station-y-mm|Station spanwise position]]
- [[station-center-z|Station centre height]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:531` — `_piece_from_run_with_od`

**Consumed by.**

- in this graph: `No-spar region start` · `Spar piece tip spanwise position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:488` · `app/services/spar_plan_service.py:495` · `cad_designer/airplane/geometry/spar_cad_insertion.py:65` · `app/services/spar_insert_service.py:165`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Euclidean distance between two points.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
