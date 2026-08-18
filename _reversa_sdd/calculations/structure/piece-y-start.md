---
name: piece-y-start
symbol: y_start
kind: quantity
unit: m
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
---

# Spar piece root spanwise position

**Definition.** Where a straight spar piece starts on the span (its own origin's y), exposed in metres so the UI can show the piece's extent.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y_start_mm = piece.spare_origin[1]
```

**Inputs.**

- [[mm-to-m-factor|Millimetre-to-metre conversion factor]]  — *× unit*

**Produced by.** `app/services/spar_plan_service.py:494` — `_piece_to_out`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Spar piece tip spanwise position` · `Segment-local split position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/spar_plan.py:208` · `frontend/hooks/useSparPlan.ts:57`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (geometric bookkeeping of a manufactured piece's extent; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `gh-1057: expose the piece's spanwise extent (``y_start``/``y_end``, m) so the UI can show where each piece runs and where the telescoping joint sits.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
