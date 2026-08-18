---
name: cots-node-own-weight
symbol: m_cots
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
  - flag/divergence
---

# COTS node own weight

**Definition.** Own weight of a component-tree node of type 'cots': the catalogue component's mass multiplied by the node quantity.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
comp.mass_g * (node.quantity or 1)
```

**Inputs.**

- [[node-quantity|Node quantity]]

**Produced by.** `app/services/component_tree_service.py:438` — `_weight_from_cots`

**Consumed by.**

- in this graph: `Node own weight`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:466 (_calculate_own_weight)` · `app/services/component_tree_service.py:106 (_roll_up_weights → total_weight_g)` · `app/services/component_tree_service.py:401 (get_aircraft_total_weight_kg)` · `frontend/components/workbench/ComponentTree.tsx:101`

**Source.** 🟢 SOURCED

> Sadraey, M.H., "Aircraft Design: A Systems Engineering Approach", Wiley 2013, §11.2 — component weight build-up: ΣW_i = W_W + W_F + W_HT + W_VT + W_E + W_LG + W_PL + W_fuel + W_C + …, with ΣW_i = W_TO at maximum take-off weight. Also Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10, sub-step b — component-group mass calculation via a tabulated weight-and-CG statement, one line item per element.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i = W_W + W_F + W_HT + W_VT + W_E + W_LG + W_PL + W_fuel + W_C + … (Sadraey §11.2); n identical items collapse to n·W_item
```

**⚠️ Divergence from the source.** Sadraey's build-up is a CLOSED enumeration — every component of the aircraft appears exactly once. The code sums only nodes the user has actually created, so the roll-up is a lower bound on W_TO, never the guaranteed total. Separately, the ×quantity multiplier is applied ONLY on this branch (component_tree_service.py:438); _weight_from_cad_shape (:455/:457) and the weight_override_g branch (:463) ignore node.quantity, so the same field means 'n instances' for a COTS node and nothing at all for the other two node kinds.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
