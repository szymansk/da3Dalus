---
name: yaw_roles
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Yaw control role set

**Definition.** Role tags counted as yaw-capable control surfaces.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{rudder, ruddervator}`

**Formula — as the code writes it.**

```
YAW_ROLES = {"rudder", "ruddervator"}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:50` — `YAW_ROLES`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Control capability flags`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:614` · `app/services/operating_point_generator_service.py:551`

**Source.** 🟢 SOURCED

> Sadraey §12.2, Table 12.4 (#7 ruddervator/V-tail; #8 drag-rudder; #11 split rudder)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
rudder = yaw; ruddervator differential = yaw
```

**⚠️ Divergence from the source.** Correct as far as it goes. Sadraey lists two further yaw producers for tailless layouts (drag-rudder, split rudder, e.g. DarkStar/B-2). A tailless RC/UAV using those would report has_yaw_control=False and have every turn/dutch-roll target skipped.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
