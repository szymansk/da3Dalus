---
name: aircraft-total-weight-kg
symbol: m_total_kg
kind: quantity
unit: kg
cluster: mass
user_visible: true
source_status: SOURCED
---

# Aircraft total weight from component tree

**Definition.** Total aircraft mass obtained by summing every root node's own weight plus its recursive children weight, converted from grams to kilograms. This is the authority that writes the 'mass' design assumption when the user builds via the component tree.

**Formula — as the code writes it.**

```
total_g += (own or 0.0) + _calculate_children_weight(db, aeroplane_id, r.id)  ...  return total_g / 1000.0 if total_g > 0 else None
```

**Inputs.** [[node-own-weight|Node own weight]] · [[node-children-weight|Node children weight (recursive)]] · [[grams-to-kg-divisor|g → kg divisor]]

**Produced by.** `app/services/component_tree_service.py:381` — `get_aircraft_total_weight_kg`

**Consumed by.**

- in this graph: [[mass-effective|Effective aircraft mass]]
- outside it: `app/services/mass_cg_service.py:160 (sync_component_tree_to_mass → mass.calculated_value)` · `app/services/component_tree_service.py:372 (_sync_aircraft_mass, called from add/update/delete node)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 — "At maximum take-off weight ΣW_i = W_TO", with ΣW_i = W_W + W_F + W_HT + W_VT + W_E + W_LG + W_PL + W_fuel + W_C + …; Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step b (aircraft mass calculation by component group).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i = W_TO  (Sadraey §11.2)
```

**⚠️ Divergence from the source.** Sadraey's ΣW_i is a closed enumeration of every component group — structure, propulsion, fuel system, hydraulic/electrical/avionics/instruments, interior furnishings, operational items, payload, fuel. The code sums whatever root nodes happen to exist, so the result is only W_TO if the user modelled everything; there is no completeness check against Sadraey's group list. Sadraey also has no notion of the total being None/absent — his method always yields a number because missing components are ESTIMATED (§10.4), never omitted.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the same user-visible 'mass' number: app/services/mass_cg_service.py:174 sync_weight_items_to_assumptions writes mass.calculated_value from aggregate_weight_items (source='weight_items'), driven by app/services/weight_items_service.py:62. Last writer wins; nothing reconciles the two (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Top-level here means parent_id IS NULL — that captures every wing, fuselage, payload, etc. since their synced groups are root nodes." — app/services/component_tree_service.py:383`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
