---
name: node-total-weight-api
symbol: m_total
kind: quantity
unit: g
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Node total weight (single-node endpoint)

**Definition.** Own weight plus recursive children weight for one node, returned by the per-node weight endpoint.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
total_weight_g=(own_weight or 0) + children_weight
```

**Inputs.**

- [[node-own-weight|Node own weight]]
- [[node-children-weight|Node children weight (recursive)]]

**Produced by.** `app/services/component_tree_service.py:427` — `calculate_weight`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/api/v2/endpoints/aeroplane/component_tree.py:134 (get_node_weight)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 (ΣW_i); Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step b (grouped weight-and-CG statement).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i, organised as component group = Σ(its elements)
```

**⚠️ Divergence from the source.** Same quantity and same source as node-total-weight-rollup, computed by a second implementation at component_tree_service.py:427. Nothing in the source calls for two evaluations.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of node-total-weight-rollup, and its only consumer is an endpoint no client calls (see node-children-weight).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
