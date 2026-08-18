---
name: ss-dod
symbol: dod
kind: parameter
unit: dimensionless (0..1]
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Depth of discharge

**Definition.** Usable fraction of rated pack capacity before landing.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.80`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:53` — `SolutionSpaceAssumptions.dod`

**Consumed by.**

- in this graph: `Mission energy at high prop efficiency` · `Mission energy at low prop efficiency` · `Required mission energy`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:377` · `app/services/powertrain_solution_space_service.py:400` · `app/services/powertrain_solution_space_service.py:412`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No depth-of-discharge figure appears in any of the three vaults. RC-Network Wiki 'Nennspannung' addresses only rated voltage; the Roxxy Motoren-Fibel addresses current and thermal limits; Sadraey (2013) §8.7 gives only a coarse mass-per-15-minutes anchor. 0.80 is unattributed — and the identical quantity is hardcoded, non-overridable, at 0.8 in the sizing service.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same physical quantity as the hardcoded 0.8 in powertrain_sizing_service.py:256, but tunable here and fixed there (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Depth of discharge (usable fraction of rated capacity)" — NO_SOURCE_FOUND`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
