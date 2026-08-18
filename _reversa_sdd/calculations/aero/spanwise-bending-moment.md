---
name: spanwise-bending-moment
symbol: M(y)
kind: quantity
unit: N·m
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Running bending moment

**Definition.** Sum of L_j·(y_j − y) over all strips outboard of y.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
bending_moment_Nm: float = Field(..., description="Running bending moment M(y): sum of L_j*(y_j - y) for all strips outboard (N·m)")
```

**Inputs.**

- [[q-dyn|Dynamic pressure]]
- [[spanwise-y-m|Strip spanwise station]]

**Produced by.** `app/schemas/spanwise_loads.py:32` — `SpanwiseLoadEntry.bending_moment_Nm`

**Consumed by.**

- in this graph: `Port root bending moment` · `Starboard root bending moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_surface_to_stations` · `compute_spar_sizing` · `frontend useSpanwiseLoads.ts:16` · `frontend/lib/sparPlanHelpers.ts:40`

**Source.** 🟡 PARTIAL

> Scholz 07_WingDesign §7.4 ('the front spar carries the primary bending moment from wing lift'; box depth 'increases toward the root, where bending moments are largest'); Sadraey §5.8 benefit 2 ('lift concentrated toward the root → smaller bending-moment arm → lighter wing spar'). Discrete formula itself not found in a source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Concept: M(y) = integral from y to b/2 of l(eta)·(eta − y) d(eta)
```

**⚠️ Divergence from the source.** Code's Σ L_j·(y_j − y) is the correct discrete form of the source's moment-arm concept; the summation is a project construct.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
