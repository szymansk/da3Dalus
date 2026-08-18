---
name: ss-catalog-esc-match
symbol: has_esc_match
kind: quantity
unit: boolean
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Catalog ESC match flag

**Definition.** True when at least one catalog ESC meets the minimum current rating.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
max_a = specs.get("max_current_a") or specs.get("continuous_current_a") ; if max_a is not None and float(max_a) >= esc_min_a: return True
```

**Inputs.**

- [[ss-esc-min|Minimum ESC current rating]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:229` — `_catalog_esc_match`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:458` · `frontend/components/workbench/PowertrainTab.tsx:553`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Motorsteller': 'Current Rating (Amperage) - The most important specification: maximum continuous current capacity determines controller size and weight. Reputable manufacturers rate continuous capacity ... Cheap imports sometimes advertise peak (pulse) capacity, which is substantially higher than continuous rating.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
ESC selection governed by maximum CONTINUOUS current capacity
```

**⚠️ Divergence from the source.** Directly contradicts the code. The matcher PREFERS max_current_a (the burst/pulse figure) over continuous_current_a, which is the exact ordering the source warns against — and it is the opposite of the preference used by the sizing service's own ESC matcher.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Prefers max_current_a (a burst rating) over continuous_current_a when both exist, i.e. the opposite preference to _find_matching_esc in the sizing service (powertrain_sizing_service.py:110), which prefers the continuous figure. Two services rate the same ESCs by different criteria.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
