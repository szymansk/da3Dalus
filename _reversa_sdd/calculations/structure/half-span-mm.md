---
name: half-span-mm
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

# Wing half-span

**Definition.** Total half-span of the wing behind a SectionGeometry, as the sum of its segment lengths.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
lengths = getattr(geometry, "_segment_lengths", None)
if not lengths:
    return 0.0  # pragma: no cover - cadquery boundary
return float(sum(lengths))
```

**Inputs.**

- [[segment-lengths|Per-segment spanwise lengths]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:787` — `_half_span_mm`

**Consumed by.**

- in this graph: `Station spanwise position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:772`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (summing segment lengths is bookkeeping. Independent of provenance: it reaches into SectionGeometry's private `_segment_lengths` from another package, and a missing attribute silently yields half-span 0, collapsing every station y_mm to 0 — an undeclared ADR 0020 fallback that would produce a degenerate plan)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Reaches into SectionGeometry's private attribute _segment_lengths from another package. Undeclared fallback: a missing attribute yields half-span 0, which collapses every station y_mm to 0 and would silently produce a degenerate plan.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
