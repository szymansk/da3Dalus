---
name: node-children-weight
symbol: m_children
kind: quantity
unit: g
cluster: mass
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
---

# Node children weight (recursive)

**Definition.** Recursive sum of the own weights of all descendants of a node.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
total += (own or 0) + children_sum
```

**Inputs.**

- [[node-own-weight|Node own weight]]

**Produced by.** `app/services/component_tree_service.py:477` — `_calculate_children_weight`

**Consumed by.**

- in this graph: `Aircraft total weight from component tree` · `Node total weight (single-node endpoint)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:402 (get_aircraft_total_weight_kg)` · `app/services/component_tree_service.py:420 (calculate_weight → WeightResponse.children_weight_g)` · `app/schemas/component_tree.py:109`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 — ΣW_i = W_W + W_F + W_HT + W_VT + W_E + W_LG + W_PL + W_fuel + W_C + …; Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step b — the weight-and-CG statement is explicitly HIERARCHICAL: component groups (wing, fuselage, empennage, powerplant, landing gear, equipment/instruments, payload) each decomposed into elements (e.g. wing main structure, ailerons, flaps, fairings, miscellaneous), every line item contributing to the summation.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i over all components, organised by component group → element (Scholz §2.2 Step 10b)
```

**⚠️ Anomaly.** children_weight_g is only ever surfaced by GET /aeroplanes/{id}/component-tree/{node_id}/weight (app/api/v2/endpoints/aeroplane/component_tree.py:123-134). Repo-wide search found no frontend fetch of that path and no MCP tool for it — the endpoint and this field have no known consumer.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
