---
name: vs_floors
kind: constant
unit: m/s
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
  - flag/anomaly
  - flag/divergence
---

# Reference-speed floors

**Definition.** Hard lower bounds applied to the three reference stall speeds.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3.0 / 2.5 / 2.0`

**Formula — as the code writes it.**

```
"vs_clean": max(3.0, vs_clean), "vs_to": max(2.5, vs_to), "vs_ldg": max(2.0, vs_ldg)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:360` — `_estimate_reference_speeds`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:401-403`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 3.0 / 2.5 / 2.0 m/s have no source in any consulted authority. Sadraey §4.3.2 derives V_s from wing loading and CL_max with no lower bound; the physical lower bound on V_s for a 0.5 kg model is set by W/S and CL_max, not by a constant. Three undeclared clamps that emit no warning when they bind (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared clamps: three magic floors with no cited source and no warning when they bind (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
