---
name: sui-mission-type-map
symbol: —
kind: parameter
unit: enum map
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mission preset → weighting key map

**Definition.** Maps stored mission preset ids onto the scoring weight categories.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `trainer,sport,aerobatic,glider,flying_wing 1:1; sailplane/motor_glider/motorglider/thermal/soarer→glider; slope_soarer→slope_soarer; wing_racer/fpv_cruiser→sport; acro_3d/warbird/three_d/3d→aerobatic; stol_bush/stol/bush→trainer`

**Formula — as the code writes it.**

```
_MISSION_TYPE_MAP = { ... }
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/suitability_service.py:89` — `_MISSION_TYPE_MAP`

**Consumed by.**

- outside it: `search_suitability:321`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils' and Lennon (1996), Ch. 1–2 supply the target categories (trainer / sport / aerobatic / glider / tailless)
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The target vocabulary is sourced; the alias mapping (wing_racer→sport, warbird→aerobatic, stol_bush→trainer, …) is a product decision with no source. 'thermal' and 'soarer' map preset ids that do not exist — unreachable entries (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 'thermal' and 'soarer' are self-declared forward-compat entries for preset ids that do not exist — unreachable map entries (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"thermal": "glider",  # forward-compat if "thermal" ever becomes a preset id
"soarer": "glider",  # forward-compat`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
