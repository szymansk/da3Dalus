---
name: station-clearance
symbol: clr
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
---

# Station packing clearance

**Definition.** One-sided skin/glue clearance inset from each surface of the real lofted section, derived from the packing factor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
clr = (1.0 - packing_factor) / 2.0 * pt.thickness
```

**Inputs.**

- [[structure--packing-factor|Packing factor]]
- [[section-thickness-analytic|Section thickness (analytic)]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:761` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: `Contained band upper bound` · `Contained band lower bound`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:762` · `cad_designer/airplane/geometry/spar_solver.py:763`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (derived entirely from the unattributed packing factor — see `packing-factor`. Note this path applies the clearance as a symmetric two-sided inset (1−packing)/2 per side of the REAL lofted section, while app/services/spar_sizing.py:323 applies the same constant as a single multiplicative factor on a chord·(t/c) estimate. No source supports either, and no source supports them differing.)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `read the contained band ``[bottom_z + clr, top_z - clr]`` (clr from ``packing_factor``)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
