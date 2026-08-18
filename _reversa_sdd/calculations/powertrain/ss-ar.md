---
name: ss-ar
symbol: AR
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Aspect ratio (solution space)

**Definition.** Wing aspect ratio from the computation context, or a fallback with a warning.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ar: float | None = ctx.get("aspect_ratio") ; if ar is None or ar <= 0: warnings.append(...) ; ar = 7.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:292` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Induced-drag factor` · `Aerodynamic power at cruise` · `Aerodynamic power at top speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🟢 SOURCED

> rcplanedesigner.com, 'Aspect Ratio - Practical limits and mission-consistent ranges': Trainer 5 / 7 / 9 (min/typical/max), Sport 4 / 5.5 / 7; gliders AR 10-25 explicitly outside the method's scope.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Trainer AR typical = 7
```

**⚠️ Divergence from the source.** 7.0 is exactly the source's trainer typical value — the best-supported of the two AR defaults in this cluster (the sizing service uses 8.0). The source stresses that AR 'is selected within mission-consistent ranges rather than optimized in isolation', which a mission-blind default cannot honour.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fallback 7.0 contradicts 8.0 used by the sizing service (powertrain_sizing_service.py:46) for the same quantity.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND for 7.0`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
