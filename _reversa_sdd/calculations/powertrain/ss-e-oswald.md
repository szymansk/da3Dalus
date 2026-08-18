---
name: ss-e-oswald
symbol: e
kind: quantity
unit: dimensionless
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
  - flag/scale
---

# Oswald efficiency (solution space)

**Definition.** Oswald span efficiency from the computation context, or a fallback with a warning.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
e_oswald: float | None = ctx.get("e_oswald") ; if e_oswald is None or e_oswald <= 0: warnings.append(...) ; e_oswald = 0.75
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:285` — `compute_solution_space`

**Consumed by.**

- in this graph: `Induced-drag factor` · `Aerodynamic power at cruise` · `Aerodynamic power at top speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2: typical airplanes e = 0.70-0.85. Scholz HAW Hamburg Klausur SS19, §1.6: takeoff/landing configuration e = 0.70-0.75, clean cruise e = 0.85-0.92.
>
> — via `aerodynamics-expert / aircraft-design-scholz`

**The source states it as.**

```
C_D = C_D,0 + C_L^2/(pi e AR)
```

**⚠️ Divergence from the source.** 0.75 is inside Anderson's typical band but at the bottom of it, and it disagrees with the 0.8 used by the sizing service for the identical quantity. Neither value is wrong against Anderson; having two is the finding.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Anderson's 0.70-0.85 and Scholz's bands are full-size-airplane data. No RC-scale Oswald factor exists in the rc-aircraft-designer vault, so neither 0.75 nor 0.8 is validated at 0.5-15 kg.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Fallback 0.75 contradicts 0.8 used by the sizing service (powertrain_sizing_service.py:45) and endurance_service.py:57 for the same quantity.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND for 0.75`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
