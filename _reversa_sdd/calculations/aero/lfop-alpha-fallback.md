---
name: lfop-alpha-fallback
symbol: alpha_trimmed
kind: constant
unit: deg
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Trim alpha fallback

**Definition.** Alpha used when the root search does not bracket a solution.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `4.0`

**Formula — as the code writes it.**

```
alpha_trimmed = 4.0  # benign default
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:528` — `_resolve_level_flight_op`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 4 deg has no basis. It is returned in the same field as a genuinely solved trim alpha, distinguished only by the operating point's name string.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: a failed trim silently returns 4° as if trimmed, and the returned OP is labelled only by name 'level_flight_fallback' (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:527-528`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
