---
name: real-front-pieces
kind: quantity
unit: -
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
---

# Buildable front pieces

**Definition.** The front-spar pieces that actually become a persisted Spare — those at or above the buildable OD floor. Sub-floor tips must not count toward telescoping detection or create a phantom segment split.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return [p for p in plan.front_pieces if p.outer_d >= NEGLIGIBLE_OD_FLOOR_MM]
```

**Inputs.**

- [[negligible-od-floor-mm|Buildable-minimum spar outer diameter]]  — *⊣ limit*
- [[piece-outer-diameter|Spar piece outer diameter]]

**Produced by.** `app/services/spar_insert_service.py:284` — `_real_front_pieces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/spar_insert_service.py:289` · `app/services/spar_insert_service.py:302` · `app/services/spar_insert_service.py:321`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (inherits the unattributed NEGLIGIBLE_OD_FLOOR_MM — see that entry. Independent of provenance: the filter is applied AFTER stock snapping may have changed outer_d, so a snap that lowers an OD below 1.0 mm removes the piece from the split plan while it remains in plan.front_pieces for _build_planned_pieces, and the two paths then disagree on how many front pieces exist)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Applied to plan.front_pieces AFTER stock snapping has possibly changed outer_d (app/services/spar_plan_service.py:193). A snap that lowers a piece's OD below 1.0 mm would silently remove it from the split plan while it remains in plan.front_pieces for _build_planned_pieces (spar_insert_service.py:182), so the two paths can disagree on how many front pieces exist.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `This guard mirrors the solver's floor so a plan that reaches this path without going through ``plan_spar`` (e.g. deserialized) stays coherent with it.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
