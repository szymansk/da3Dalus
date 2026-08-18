---
name: station-y-mm
symbol: y_mm
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - surface/user-visible
---

# Station spanwise position

**Definition.** Absolute spanwise position of a solver station, from the station's span fraction times the wing half-span.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y_mm=pt.y_span * _half_span_mm(geometry),
```

**Inputs.**

- [[half-span-mm|Wing half-span]]
- [[y-spans-grid|Spanwise sampling grid]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:772` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: `Spar piece direction unit vector` · `Spar piece length` · `Reinforcement half-reach` · `Spanwise position to segment index`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:270` · `cad_designer/airplane/geometry/spar_solver.py:484` · `cad_designer/airplane/geometry/spar_solver.py:528` · `cad_designer/airplane/geometry/spar_solver.py:529` · `app/services/spar_plan_service.py:233` · `app/services/spar_plan_service.py:482`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (span-fraction to absolute-position bookkeeping; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
