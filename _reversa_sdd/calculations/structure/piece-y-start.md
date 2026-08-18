---
name: piece-y-start
symbol: y_start
kind: quantity
unit: m
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Spar piece root spanwise position

**Definition.** Where a straight spar piece starts on the span (its own origin's y), exposed in metres so the UI can show the piece's extent.

**Formula — as the code writes it.**

```
y_start_mm = piece.spare_origin[1]
```

**Inputs.** [[mm-to-m-factor|Millimetre-to-metre conversion factor]]

**Produced by.** `app/services/spar_plan_service.py:494` — `_piece_to_out`

**Consumed by.**

- in this graph: [[piece-y-end|Spar piece tip spanwise position]] · [[split-local-length|Segment-local split position]]
- outside it: `app/schemas/spar_plan.py:208` · `frontend/hooks/useSparPlan.ts:57`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (geometric bookkeeping of a manufactured piece's extent; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `gh-1057: expose the piece's spanwise extent (``y_start``/``y_end``, m) so the UI can show where each piece runs and where the telescoping joint sits.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
