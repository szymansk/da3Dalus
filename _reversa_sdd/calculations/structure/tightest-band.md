---
name: tightest-band
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

# Tightest containment band for a piece

**Definition.** The narrowest containable OD across all stations the piece covers — the denominator of utilisation and the feasibility threshold.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
tightest = _max_od_for_run(run.stations)
```

**Inputs.**

- [[max-od-for-run|Largest containable OD for a run]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:532` — `_piece_from_run_with_od`

**Consumed by.**

- in this graph: `Spar piece feasibility` · `Spar piece utilisation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:539` · `cad_designer/airplane/geometry/spar_solver.py:540`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the spar must fit within the airfoil section; insufficient depth produces oil-canning visible in the finished profile
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Qualitative containment requirement only.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
