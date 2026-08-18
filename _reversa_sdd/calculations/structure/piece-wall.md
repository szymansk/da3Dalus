---
name: piece-wall
symbol: wall
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Spar piece wall thickness

**Definition.** Wall thickness of a spar piece, derived from its outer and inner diameters and floored at zero.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return max(0.0, (self.outer_d - self.inner_d) / 2.0)
```

**Inputs.**

- [[piece-outer-diameter|Spar piece outer diameter]]
- [[piece-bore|Spar piece inner diameter]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:124` — `SparPiece.wall`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:135` · `app/services/spar_plan_service.py:502` · `app/schemas/spar_plan.py:192` · `frontend/hooks/useSparPlan.ts:46` · `frontend/lib/sparPlanHelpers.ts:139`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the Holmsteg (web) thickness and the boom/wall dimensioning "depends on flight loads; insufficient web height can result in spar oil-canning (buckling)"
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
No closed form. The wall of a tube is geometrically (OD − ID)/2.
```

**⚠️ Divergence from the source.** The geometry is trivially correct. The undeclared clamp is not sourced: max(0.0, ...) silently reports wall = 0 when inner_d exceeds outer_d rather than surfacing an inconsistent piece (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared clamp: max(0.0, ...) silently reports wall=0 when inner_d exceeds outer_d rather than surfacing the inconsistency.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
