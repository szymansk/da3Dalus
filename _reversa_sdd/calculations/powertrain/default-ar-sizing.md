---
name: default-ar-sizing
symbol: _DEFAULT_AR
kind: constant
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default aspect ratio (sizing)

**Definition.** RC-typical wing aspect ratio used when neither request nor context supplies AR.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `8.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:46` — `_DEFAULT_AR`

**Consumed by.**

- in this graph: `Resolved aspect ratio`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:182`

**Source.** 🟢 SOURCED

> rcplanedesigner.com, 'Aspect Ratio - Wingspan vs Wing Area in RC Airplanes: Practical limits and mission-consistent ranges' — mission-consistent table: Trainer min 5 / typical 7 / max 9; Sport min 4 / typical 5.5 / max 7. Gliders (AR 10-25) explicitly out of scope of that method.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Trainer AR: 5 (min) / 7 (typical) / 9 (max);  Sport AR: 4 / 5.5 / 7
```

**⚠️ Divergence from the source.** 8.0 lies inside the trainer range (5-9) but above the trainer typical (7) and entirely outside the sport range (max 7). As a single mission-blind default it silently assumes a trainer-like, high-AR airframe.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Conflicts with the solution space's AR fallback of 7.0 (powertrain_solution_space_service.py:292) for the same quantity.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
