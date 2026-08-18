---
name: default_loiter_s
kind: constant
unit: s
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Default loiter duration

**Definition.** Desired loiter duration in the default profile.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `600`

**Formula — as the code writes it.**

```
"loiter_s": 600
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:210` — `_default_profile`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 600 s has no source. Sadraey §4.2.5.4 makes loiter duration E an input to the endurance fuel fraction (Eq. 4.24), i.e. a mission requirement — not a class default. Dead parameter: no consumer in the repo.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer anywhere in the repo; the loiter_endurance target velocity is computed from vs_clean/cruise and never from loiter_s.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
