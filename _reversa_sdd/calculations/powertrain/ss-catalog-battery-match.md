---
name: ss-catalog-battery-match
symbol: has_battery_match
kind: quantity
unit: boolean
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
---

# Catalog battery match flag

**Definition.** True when at least one catalog battery meets both the capacity floor and the margin-inclusive C-rate floor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cap = specs.get("capacity_mah") ; c_rating = specs.get("c_rating") or specs.get("discharge_c") ; if cap is not None and c_rating is not None: if float(cap) >= cap_mah_min and float(c_rating) >= c_min: return True
```

**Inputs.**

- [[ss-cap-mah|Minimum battery capacity]]  — *⊣ limit*
- [[ss-c-min|Required battery C-rate]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:218` — `_catalog_battery_match`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:457` · `frontend/components/workbench/PowertrainTab.tsx:553`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Nennspannung' establishes the pack rating conventions (voltage per cell, capacity, discharge under load). C-rating as a catalog spec is standard RC practice but is not defined in a citable section of any vault.
>
> — via `rc-aircraft-designer`

**⚠️ Anomaly.** Reads the C-rate under the keys c_rating / discharge_c, while the performance module reads the same catalog under the key c_rate (app/api/v2/endpoints/aeroplane/powertrain_performance.py:124) — three spellings of one spec field across the cluster.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Return True if any battery in the catalog meets capacity AND C-rate floors."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
