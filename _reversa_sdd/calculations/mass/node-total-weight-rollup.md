---
name: node-total-weight-rollup
symbol: m_total
kind: quantity
unit: g
cluster: mass
user_visible: true
source_status: SOURCED
---

# Node total weight (tree roll-up)

**Definition.** Own weight plus the total weight of every child, computed in a post-order traversal when the whole tree is served.

**Formula — as the code writes it.**

```
node.total_weight_g = (own or 0.0) + sum(c.total_weight_g for c in node.children)
```

**Inputs.** [[node-own-weight|Node own weight]]

**Produced by.** `app/services/component_tree_service.py:106` — `_roll_up_weights`

**Consumed by.**

- outside it: `app/services/component_tree_service.py:141 (ComponentTreeResponse)` · `app/schemas/component_tree.py:78` · `frontend/components/workbench/ComponentTree.tsx:102` · `frontend/components/workbench/ComponentTree.tsx:122 (root sum shown as tree total)` · `frontend/components/workbench/ComponentTree.tsx:138`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 (ΣW_i); Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step b — grouped weight-and-CG statement in which a group's weight is the sum of its element rows.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i, organised as component group = Σ(its elements)
```

**⚠️ Divergence from the source.** Not a formula divergence but a producer divergence: the identical group-sum is implemented twice against two separate DB traversals — _roll_up_weights (component_tree_service.py:106, post-order over the built tree) and calculate_weight (:427, own + _calculate_children_weight). Both realise Scholz's single grouped statement.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two independent producers of the same number: this roll-up (line 106) and calculate_weight (line 427, own + _calculate_children_weight). Same intent, separate implementations and separate DB traversals.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
