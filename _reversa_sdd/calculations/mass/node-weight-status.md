---
name: node-weight-status
symbol: weight_status
kind: quantity
unit: enum (dimensionless)
cluster: mass
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
---

# Node weight completeness status

**Definition.** Whether the weight of a subtree is fully known: 'valid' (own weight present / all children valid), 'partial' (mixed, or own present but all children invalid), 'invalid' (nothing known).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
leaf: "valid" if has_own else "invalid"; non-leaf: all_valid → "valid"; all_invalid → "partial" if has_own else "invalid"; else "partial"
```

**Inputs.**

- [[node-own-weight-source|Own weight provenance]]

**Produced by.** `app/services/component_tree_service.py:108` — `_roll_up_weights`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/component_tree.py:81` · `frontend/components/workbench/ComponentTree.tsx:103` · `frontend/components/workbench/ComponentTree.tsx:123` · `frontend/components/workbench/ComponentTree.tsx:175`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `"Logic (gh#78)" — app/services/component_tree_service.py:92`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
