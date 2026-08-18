---
name: station-center-z
symbol: center_z
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Station centre height

**Definition.** The StationData mid-height the solver places a spar axis on, copied from the sampled SectionPoint.

**Formula — as the code writes it.**

```
center_z=pt.center_z,
```

**Inputs.** [[section-center-z-analytic|Section mid-height (analytic)]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:775` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: [[axis-z-at|Straight-piece axis height at a station]] · [[piece-direction-vector|Spar piece direction unit vector]] · [[piece-length|Spar piece length]] · [[root-centreline-z|Root centreline height]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:271` · `cad_designer/airplane/geometry/spar_solver.py:528` · `cad_designer/airplane/geometry/spar_solver.py:529` · `cad_designer/airplane/geometry/spar_solver.py:586` · `cad_designer/airplane/geometry/spar_solver.py:601` · `cad_designer/airplane/geometry/spar_solver.py:618`

**Source.** 🟡 PARTIAL

> Lennon, The Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 13, Figs. 6-8; RC-Network Wiki, "Mechanische Spannung", https://wiki.rc-network.de/wiki/Mechanische_Spannung
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Same neutral-axis reference as `section-center-z-analytic`; this is a plain copy of that value into the solver's station record.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
