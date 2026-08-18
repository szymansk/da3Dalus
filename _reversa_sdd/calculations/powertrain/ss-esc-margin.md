---
name: ss-esc-margin
symbol: esc_margin
kind: parameter
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# ESC current margin

**Definition.** Safety multiplier applied to peak current to get the minimum ESC rating.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.4`

**Formula — as the code writes it.**

```
esc_min = i_peak * esc_margin
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:59` — `SolutionSpaceAssumptions.esc_margin`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Minimum ESC current rating`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:149` · `app/services/powertrain_solution_space_service.py:389`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** RC-Network Wiki 'Motorsteller' establishes that a margin is needed and why (continuous vs pulse ratings, BEC load, thermal sizing) but states no multiplier. The 1.4 factor sizes a safety-critical component with no source of any kind (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number, no source, directly sizes a safety-critical component (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "ESC current rating margin multiplier (ESC_min = I_peak × esc_margin)" — NO_SOURCE_FOUND`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
