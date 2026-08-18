---
name: piece-y-end
symbol: y_end
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

# Spar piece tip spanwise position

**Definition.** Where a straight spar piece ends on the span, derived from its origin plus its length along the span component of its direction vector. For a telescoping run this is the next piece's y_start, i.e. the joint position.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y_end_mm = y_start_mm + piece.length * piece.spare_vector[1]
```

**Inputs.**

- [[piece-y-start|Spar piece root spanwise position]]
- [[piece-length|Spar piece length]]
- [[piece-direction-vector|Spar piece direction unit vector]]
- [[mm-to-m-factor|Millimetre-to-metre conversion factor]]  — *× unit*

**Produced by.** `app/services/spar_plan_service.py:495` — `_piece_to_out`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/spar_plan.py:216` · `frontend/hooks/useSparPlan.ts:58`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (geometric bookkeeping; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `The extent is derived from the piece's own geometry — the root is its ``spare_origin`` y, the tip is that plus the piece length along its span direction (``spare_vector`` y) — then converted mm->m.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
