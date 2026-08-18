---
name: fe_wing_area
symbol: S_ref
kind: quantity
unit: m^2
cluster: perf-envelope
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - flag/divergence
---

# Reference wing area

**Definition.** Reference area taken from the ASB airplane conversion.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
s_ref = asb_airplane.s_ref (raise InternalError if None or <= 0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:571` — `_get_wing_area_m2`

**Consumed by.**

- in this graph: `Aspect ratio (gust path)` · `Mean geometric chord` · `Negative maneuver load factor` · `Positive maneuver load factor` · `Stall speed (1 g)` · `Wing loading (gust path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Reference area convention owned by the geometry/ASB layer.
>
> — via `aero`

**The source states it as.**

```
S_ref from ASB airplane conversion
```

**⚠️ Divergence from the source.** Correctly raises InternalError when absent or <= 0 — contrast fe_b_ref, which swallows the same class of failure.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
