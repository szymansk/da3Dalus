---
name: ss-eta-esc
symbol: eta_esc
kind: parameter
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# ESC efficiency (solution space)

**Definition.** Flat ESC efficiency assumed for the whole envelope.

**Value.** `0.94`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:47` — `SolutionSpaceAssumptions.eta_esc`

**Consumed by.**

- in this graph: [[ss-p-cruise-hi-e|Electrical cruise power at high prop efficiency]] · [[ss-p-cruise-lo-e|Electrical cruise power at low prop efficiency]] · [[ss-p-cruise-mid|Electrical cruise power (mid band)]] · [[ss-p-elec|Electrical power required]] · [[ss-p-top-hi-e|Electrical peak power at high prop efficiency]] · [[ss-p-top-lo-e|Electrical peak power at low prop efficiency]] · [[ss-p-top-mid|Electrical peak power (mid band)]]
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
