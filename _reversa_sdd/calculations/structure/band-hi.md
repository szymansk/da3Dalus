---
name: band-hi
symbol: band_hi
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: PARTIAL
---

# Contained band upper bound

**Definition.** Upper z limit of the region a spar may occupy at the station: the section top surface inset by the packing clearance.

**Formula — as the code writes it.**

```
band_hi = pt.top_z - clr
```

**Inputs.** [[section-top-z-analytic|Section upper surface height (analytic)]] · [[station-clearance|Station packing clearance]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:763` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: [[max-od-for-run|Largest containable OD for a run]] · [[max-od-from-stations|Containment-band OD limit at governing station]] · [[rod-outer-fallback-1mm|Rod sizing outer-dimension floor]] · [[section-depth-at-governing|Section depth at the governing station]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:282` · `cad_designer/airplane/geometry/spar_solver.py:293` · `cad_designer/airplane/geometry/spar_solver.py:543` · `cad_designer/airplane/geometry/spar_solver.py:604` · `cad_designer/airplane/geometry/spar_solver.py:767` · `app/services/spar_plan_service.py:234`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm; Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13 (flanges as far from the neutral axis as the section allows)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Containment principle only; the inset magnitude derives from the unattributed packing factor.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
