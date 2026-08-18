---
name: grid_best_controls
kind: quantity
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Grid-search control result

**Definition.** Control deflections returned by the grid search.

**Formula — as the code writes it.**

```
best_controls = {}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:840` — `_grid_search_trim`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:945-950 (overwrites best_controls)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Not a calculation — an empty dict. Per Sadraey §12.5 longitudinal trim is achieved BY elevator deflection; a trim result reporting no control deflection is not a trim result. When the grid path wins it overwrites the Opti-solved deflections with {}, so the persisted point claims zero elevator for a condition that required one, and the grid evaluation itself runs with zero controls and no flap (a 'landing' target evaluated clean).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Always empty: when the grid fallback wins it overwrites the Opti-solved elevator/aileron/rudder deflections with {} , so the persisted OP reports zero control deflection for a point that needed one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
