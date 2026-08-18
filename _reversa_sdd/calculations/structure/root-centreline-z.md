---
name: root-centreline-z
symbol: root_z
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
  - flag/anomaly
---

# Root centreline height

**Definition.** Mean of the two halves' root-station mid-heights — the height a straight collinear carry-through rod or reinforcement runs at.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
root_z = (left[0].center_z + right[0].center_z) / 2.0
```

**Inputs.**

- [[station-center-z|Station centre height]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:601` — `_straight_collinear_in_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:603` · `cad_designer/airplane/geometry/spar_solver.py:604` · `cad_designer/airplane/geometry/spar_solver.py:618` · `cad_designer/airplane/geometry/spar_solver.py:624`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Steckung (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Steckung — a straight carry-through member must transfer the bending moment from one main spar to the other; Sadraey, Aircraft Design (Wiley 2013), §7.9.3 — structural designers "prefer to carry the wing main spar through the fuselage so that aircraft structural integrity is maintained"
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
Both sources establish the carry-through principle; neither gives the mean-of-two-root-mid-heights arithmetic.
```

**⚠️ Anomaly.** Two producers of the identical expression: spar_solver.py:601 (_straight_collinear_in_envelope) and spar_solver.py:618 (_reinforcement_piece).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Geometry-derived bent-pin trigger (spec §"Defaults"): the straight rod runs along the root centreline z; at every station the rod's z is that constant root z, and it must lie inside ``[band_lo, band_hi]``. Under strong dihedral the outboard band rises away from the root z → the rod exits → bent-pin.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
