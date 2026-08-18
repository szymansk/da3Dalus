---
name: default-s-ref-sizing
symbol: _DEFAULT_S_REF_M2
kind: constant
unit: m^2
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default wing reference area (sizing)

**Definition.** RC-typical wing area used when neither request nor context supplies S_ref.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.5`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:47` — `_DEFAULT_S_REF_M2`

**Consumed by.**

- in this graph: `Resolved wing reference area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:189`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source in any vault prescribes a default wing area. The RC vault approaches sizing through wing loading (rcplanedesigner 'Wing area / wing loading as a practical relation'; Lennon Ch. 18 wing-loading nomograph), i.e. S is derived from mass and a target loading, never defaulted as a bare area.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Conflicts with the solution space's S_ref fallback of 0.25 m2 (powertrain_solution_space_service.py:278) — a 2x disagreement on the same fallback. Also duplicated at powertrain_sizing_modal_service.py:34.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
