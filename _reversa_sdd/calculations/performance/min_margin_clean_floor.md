---
name: min_margin_clean_floor
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/divergence
---

# Clean-margin floor

**Definition.** Lower clamp on the clean stall margin used for the cold-start V_s estimate.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.05`

**Formula — as the code writes it.**

```
min_margin_clean = max(1.05, float(goals.get("min_speed_margin_vs_clean", 1.20)))
```

**Inputs.**

- [[default_min_speed_margin_vs_clean|Default clean stall margin]]  — *⤵ fallback*

**Produced by.** `app/services/operating_point_generator_service.py:336` — `_estimate_reference_speeds`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:348`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1.05 has no source. It also has no safety meaning: at 1.05·V_s the load-factor margin to stall is only 1.05² = 1.10 g, far below any cited practice (Lennon Ch. 4 asks for 20 %).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
