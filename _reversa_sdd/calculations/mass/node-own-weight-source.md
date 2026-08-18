---
name: node-own-weight-source
symbol: own_weight_source
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

# Own weight provenance

**Definition.** Provenance tag for node_own_weight: one of 'override' \| 'cots' \| 'calculated' \| 'none'.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
returned as the second tuple element of _calculate_own_weight: "override" | "cots" | "calculated" | "none"
```

**Inputs.**

- [[node-own-weight|Node own weight]]

**Produced by.** `app/services/component_tree_service.py:461` — `_calculate_own_weight`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Node weight completeness status`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:101 (_roll_up_weights has_own)` · `app/schemas/component_tree.py:77` · `frontend/components/workbench/ComponentTree.tsx:100`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
