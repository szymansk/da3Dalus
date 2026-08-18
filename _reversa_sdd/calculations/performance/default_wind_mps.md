---
name: default_wind_mps
kind: constant
unit: m/s
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/perf-oppoints
  - class/numerical-tolerance
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Default wind speed

**Definition.** Expected wind speed in the default profile.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
"wind_mps": 0.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:202` — `_default_profile`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.0 is a null default for a parameter with no consumer anywhere in the repo. No source is needed for a value that is never read; the finding is the dead parameter.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer: wind_mps is declared in the default profile and in app/schemas/flight_profile.py:70 ("helps pick conservative takeoff and approach operating points") but no operating-point calculation reads it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
