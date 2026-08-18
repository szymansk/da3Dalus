---
name: end_battery_dev_threshold
symbol: 30%
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
---

# Battery-mass deviation threshold

**Definition.** Relative deviation above which the battery-mass cross-check warns.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.30`

**Formula — as the code writes it.**

```
BATTERY_MASS_DEVIATION_THRESHOLD = 0.30  # 30%
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:69` — `BATTERY_MASS_DEVIATION_THRESHOLD`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Battery-mass deviation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> No source for 30%.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
