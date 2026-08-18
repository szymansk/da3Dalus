---
name: node-own-weight
symbol: m_own
kind: quantity
unit: g
cluster: mass
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Node own weight

**Definition.** The weight a single tree node contributes on its own (excluding descendants), resolved by a fixed precedence chain: manual override → COTS catalogue mass → CAD-shape density calculation → none.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if node.weight_override_g is not None: return node.weight_override_g, "override"; cots_weight = _weight_from_cots(db, node) ...; cad_weight = _weight_from_cad_shape(db, node) ...; return None, "none"
```

**Inputs.**

- [[weight-override-g|Manual node weight override]]
- [[cots-node-own-weight|COTS node own weight]]
- [[cad-shape-own-weight-surface|CAD shape own weight — surface print]]
- [[cad-shape-own-weight-volume|CAD shape own weight — solid print]]

**Produced by.** `app/services/component_tree_service.py:461` — `_calculate_own_weight`

**Consumed by.**

- in this graph: `Aircraft total weight from component tree` · `Node children weight (recursive)` · `Own weight provenance` · `Node total weight (single-node endpoint)` · `Node total weight (tree roll-up)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:136 (get_tree own_weights map)` · `app/services/component_tree_service.py:401 (get_aircraft_total_weight_kg)` · `app/services/component_tree_service.py:419 (calculate_weight)` · `app/services/component_tree_service.py:489 (_calculate_children_weight)` · `app/schemas/component_tree.py:74 (own_weight_g)` · `frontend/components/workbench/ComponentTree.tsx:101`

**Source.** 🟡 PARTIAL

> Sadraey, M.H., Wiley 2013, §10.4 — the four sources from which each component weight is obtained, in descending order of directness: (1) mass = volume × density, (2) actual published component weight data (Table 10.5), (3) author-derived empirical calibration factors, (4) published empirical equations (Roskam, Torenbeek, Schmitt et al.).
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Sadraey's four sources are ingredients that COMBINE into one equation per component; the code turns them into a mutually-exclusive precedence chain (override → cots → cad_shape → none). The ordering is defensible against §10.4 (measured beats derived) but the chain itself has no citable form. Note the chain also inherits the quantity asymmetry: whichever branch fires determines whether node.quantity is honoured at all.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
