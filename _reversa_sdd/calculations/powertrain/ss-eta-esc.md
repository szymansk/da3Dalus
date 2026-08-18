---
name: ss-eta-esc
symbol: eta_esc
kind: parameter
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# ESC efficiency (solution space)

**Definition.** Flat ESC efficiency assumed for the whole envelope.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.94`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:47` — `SolutionSpaceAssumptions.eta_esc`

**Consumed by.**

- in this graph: `Electrical cruise power at high prop efficiency` · `Electrical cruise power at low prop efficiency` · `Electrical cruise power (mid band)` · `Electrical power required` · `Electrical peak power at high prop efficiency` · `Electrical peak power at low prop efficiency` · `Electrical peak power (mid band)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:360` · `app/services/powertrain_solution_space_service.py:361`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Neither the Roxxy Motoren-Fibel ESC/PWM chapter nor RC-Network Wiki 'Motorsteller' quotes an efficiency figure. Both treat ESC losses qualitatively only (switching/commutation losses, timing quality, BEC type, firmware tuned for efficiency vs peak RPM vs throughput). 0.94 is unattributed in every vault consulted.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `field description: "ESC efficiency (modern ESC typical)" — NO_SOURCE_FOUND`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
