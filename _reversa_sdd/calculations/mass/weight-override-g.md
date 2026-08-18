---
name: weight-override-g
symbol: m_override
kind: parameter
unit: g
cluster: mass
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/mass
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Manual node weight override

**Definition.** User-entered weight for a component-tree node; takes precedence over both the COTS catalogue mass and the density-derived CAD weight.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `None (nullable, app/models/component_tree.py:59)`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:463` — `_calculate_own_weight`

**Consumed by.**

- in this graph: `Node own weight`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:464 (returned as own weight, source='override')` · `frontend/components/workbench/ComponentTree.tsx:100`

**Source.** 🟡 PARTIAL

> Sadraey, M.H., Wiley 2013, §10.4 — source #2 of the four sources of the weight equations is "actual published data on weight of various components (Table 10.5 — actual component weights for 16 specific aircraft from home-built to large cargo)", used to ground and validate the empirical equations. That establishes measured/actual component weight as the superior input where it exists.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Sadraey uses measured component weights to CALIBRATE the equations, not to bypass them per item. The code's precedence (override wins outright) is an app decision with no equation behind it. Concrete defect: the override is not multiplied by node.quantity (component_tree_service.py:463-464), so an override on a node representing 4 identical items reports the weight of one — this breaks Sadraey §11.2's ΣW_i over all n components.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Not multiplied by node.quantity — an override on a node with quantity=4 yields the weight of one unit.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
