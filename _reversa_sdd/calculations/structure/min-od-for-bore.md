---
name: min-od-for-bore
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
  - flag/anomaly
---

# Minimum OD to carry a bore

**Definition.** Floor on an inner piece's outer diameter so a minimal wall remains around its enlarged telescoping bore; forces OD to be non-increasing outboard.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
min_od_for_bore = bore + 2.0 * spec.telescope_clearance_mm
if ods[i] < min_od_for_bore:
    ods[i] = min_od_for_bore
```

**Inputs.**

- [[piece-bore|Spar piece inner diameter]]
- [[telescope-clearance-mm|Telescoping radial clearance]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:426` — `plan_spar`

**Consumed by.**

- in this graph: `Spar piece outer diameter`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:428`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer. RC-Network Wiki "Holm" says wall/web dimensioning "depends on flight loads" but gives no minimum wall. The code sets the "minimal wall" equal to the telescoping slip-fit clearance (0.5 mm radial) — reusing an ASSEMBLY tolerance as a STRUCTURAL minimum wall thickness. No source read treats those as the same quantity, and they are not: one is set by glue-gap and manufacturing tolerance, the other by local buckling and crushing of the tube wall.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** The 'minimal wall' is set equal to the telescoping clearance (0.5 mm radial), reusing a slip-fit dimension as a structural minimum wall thickness. Those are unrelated engineering quantities and no source justifies either as the other.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `The inner bore sets a floor on the inner OD (bore + a minimal wall), so the root piece grows to satisfy the whole telescoping stack. This also enforces OD non-increasing outboard.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
