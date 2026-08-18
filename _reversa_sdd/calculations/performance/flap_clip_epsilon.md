---
name: flap_clip_epsilon
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: numerical-tolerance
tags:
  - cluster/perf-oppoints
  - class/numerical-tolerance
  - source/no-source-found
  - flag/divergence
---

# Flap-clip warning tolerance

**Definition.** Tolerance before a clip is reported as a warning.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
if abs(requested) > limit + 1e-6:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:102` — `_clip_flap_to_ted_limit`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:103-106`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1e-6 deg is a floating-point comparison tolerance. No engineering source; none needed, but it is undocumented.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
