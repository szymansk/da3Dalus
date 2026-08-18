---
name: max-od-for-run
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
---

# Largest containable OD for a run

**Definition.** Largest straight-tube outer diameter that fits every station's contained band when the axis follows the run's root-to-tip line. The tightest constraint along the run wins.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
best = float("inf")
for s in run:
    axis_z = _axis_z_at(run, s)
    best = min(best, 2.0 * (axis_z - s.band_lo), 2.0 * (s.band_hi - axis_z))
return max(0.0, best)
```

**Inputs.**

- [[axis-z-at|Straight-piece axis height at a station]]
- [[band-lo|Contained band lower bound]]  — *⊣ limit*
- [[band-hi|Contained band upper bound]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:293` — `_max_od_for_run`

**Consumed by.**

- in this graph: `Tightest containment band for a piece`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:532`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — spar depth is bounded by the airfoil section, and insufficient depth causes visible oil-canning of the finished profile; Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The principle that the tightest section along a straight run bounds a straight spar's outer dimension is attributable qualitatively; the min-over-stations arithmetic is not stated by any source.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
