---
name: default-eta-esc-endurance
symbol: DEFAULT_ETA_ESC
kind: constant
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Default ESC efficiency

**Definition.** Flat ESC efficiency used by the sizing sweep when the request does not override it.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.94`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:55` — `DEFAULT_ETA_ESC`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Combo total propulsive efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:237`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Neither the Roxxy Motoren-Fibel ESC chapter nor RC-Network Wiki 'Motorsteller' quotes an ESC efficiency figure. Both discuss ESC losses only qualitatively (switching losses, timing quality, BEC type, firmware optimisation targets). The 0.94 value has no attribution in any vault consulted.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated as the eta_esc default at app/schemas/powertrain_solution_space.py:48.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Modern ESC`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
