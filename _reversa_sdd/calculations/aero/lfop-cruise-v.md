---
name: lfop-cruise-v
symbol: cruise_v
kind: constant
unit: m/s
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Assumed cruise speed (level-flight solve)

**Definition.** Representative cruise speed used for the fallback level-flight operating point.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `15.0`

**Formula — as the code writes it.**

```
cruise_v = 15.0  # m/s — safe guess for RC/UAV models
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:502` — `_resolve_level_flight_op`

**Consumed by.**

- in this graph: `Level-flight target lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `OperatingPointSchema.velocity (line 533)`

**Source.** 🔴 NO SOURCE FOUND

> No numeric default cruise speed found in the RC-Network Wiki / rcplanedesigner material consulted
>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 15 m/s is within the plausible RC/UAV band but is a guess presented to the user as an operating-point velocity (it reaches OperatingPointSchema.velocity at line 533). Because it also feeds cl_target quadratically, a factor-of-two speed error becomes a factor-of-four CL error.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:502`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
