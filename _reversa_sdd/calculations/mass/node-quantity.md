---
name: node-quantity
symbol: n
kind: parameter
unit: count
cluster: mass
user_visible: true
source_status: PARTIAL
---

# Node quantity

**Definition.** How many identical instances of a COTS component the node represents.

**Value.** `1 (app/models/component_tree.py:36, app/schemas/component_tree.py:28)`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:438` — `_weight_from_cots (consumer); DB default in app/models/component_tree.py:36`

**Consumed by.**

- in this graph: [[cots-node-own-weight|COTS node own weight]]
- outside it: `app/services/component_tree_service.py:438` · `app/services/component_tree_service.py:616 / :626 (servo sync sets it)`

**Source.** 🟡 PARTIAL

> Sadraey, M.H., Wiley 2013, §11.2 — the weight summation runs over n components; Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step b — the weight-and-CG statement table lists each component group's elements with weight and three CG coordinates per row.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Neither source defines a per-line 'quantity' multiplier — both enumerate each physical item as its own row, which is the reason the concept has no citable equation. The code's asymmetry is a genuine defect against Sadraey §11.2's requirement that ΣW_i cover every component: quantity is honoured only for node_type=='cots' (component_tree_service.py:438) and silently dropped for cad_shape (:455/:457) and for weight_override_g (:463).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only honoured for node_type=='cots'. Ignored by _weight_from_cad_shape and by weight_override_g.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
