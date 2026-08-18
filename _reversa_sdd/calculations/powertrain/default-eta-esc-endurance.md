---
name: default-eta-esc-endurance
symbol: DEFAULT_ETA_ESC
kind: constant
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default ESC efficiency

**Definition.** Flat ESC efficiency used by the sizing sweep when the request does not override it.

**Value.** `0.94`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:55` — `DEFAULT_ETA_ESC`

**Consumed by.**

- in this graph: [[combo-eta-total|Combo total propulsive efficiency]]
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
