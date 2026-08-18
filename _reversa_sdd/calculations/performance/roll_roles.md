---
name: roll_roles
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

# Roll control role set

**Definition.** Role tags counted as roll-capable control surfaces.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{aileron, elevon, flaperon}`

**Formula — as the code writes it.**

```
ROLL_ROLES = {"aileron", "elevon", "flaperon"}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:49` — `ROLL_ROLES`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Control capability flags`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:615` · `app/services/operating_point_generator_service.py:550`

**Source.** 🟢 SOURCED

> Sadraey §12.2, Table 12.4 and 'Unconventional Control Surfaces' (elevon, flaperon, taileron, spoileron)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
aileron (primary roll); elevon differential = roll; flaperon differential = roll
```

**⚠️ Divergence from the source.** Complete for the surface types the app models. Sadraey also lists taileron and spoileron as roll producers; absent here, but the app has no such role tags, so no defect.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
