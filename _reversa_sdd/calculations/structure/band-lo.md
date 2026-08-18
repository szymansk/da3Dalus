---
name: band-lo
symbol: band_lo
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

# Contained band lower bound

**Definition.** Lower z limit of the region a spar may occupy at the station: the section bottom surface inset by the packing clearance.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
band_lo = pt.bottom_z + clr
```

**Inputs.**

- [[section-bottom-z-analytic|Section lower surface height (analytic)]]
- [[station-clearance|Station packing clearance]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:762` — `build_stations_from_geometry`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Largest containable OD for a run` · `Containment-band OD limit at governing station` · `Rod sizing outer-dimension floor` · `Section depth at the governing station`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:280` · `cad_designer/airplane/geometry/spar_solver.py:293` · `cad_designer/airplane/geometry/spar_solver.py:543` · `cad_designer/airplane/geometry/spar_solver.py:603` · `cad_designer/airplane/geometry/spar_solver.py:767` · `app/services/spar_plan_service.py:234`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the Holmgurte are "positioned at the maximum distance apart (top and bottom of the airfoil)", bounded by the section surfaces; Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The containment principle (the spar lives between the section's lower and upper surfaces, inset by the covering) is attributable; the inset magnitude is not.
```

**Cited in the code itself.** ```band_lo``/``band_hi`` are the *contained* z-band at this station's spar chord location, i.e. already inset by the skin/packing clearance: a tube of outer diameter ``D`` centred on ``center_z`` fits iff ``[center_z - D/2, center_z + D/2]`` lies inside ``[band_lo, band_hi]``.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
