---
name: usable-capacity-fraction-sizing
symbol: 0.8
kind: constant
unit: dimensionless
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

# Usable capacity fraction (sizing)

**Definition.** Fraction of rated capacity assumed usable before the pack must be landed — the depth of discharge of the sizing path.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.8`

**Formula — as the code writes it.**

```
flight_time_h = (capacity_ah / cruise_current_a) * 0.8
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:256` — `_evaluate_motor_battery_combo`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Estimated flight time (hours)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:257`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No depth-of-discharge figure appears in any vault consulted. Sadraey (2013) §8.7 gives only the coarse energy statement that a 2-hp electric motor needs ~400 g of battery for 15 minutes; RC-Network Wiki and the Roxxy Motoren-Fibel discuss LiPo voltage and current ratings but state no usable-capacity fraction. The 0.8 is unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no explanation, and a second producer of depth-of-discharge: the solution space exposes the same physical concept as a tunable field `dod` defaulting to 0.80 (app/schemas/powertrain_solution_space.py:53). Here it is hardcoded and cannot be overridden (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND — inline literal with no comment`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
