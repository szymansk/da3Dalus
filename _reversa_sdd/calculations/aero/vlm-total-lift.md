---
name: vlm-total-lift
symbol: total_lift
kind: quantity
unit: N
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Accumulated total lift

**Definition.** Running sum of all strip lifts over the whole airplane.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
total_lift += lift
```

**Inputs.**

- [[vlm-strip-lift|Strip lift force]]

**Produced by.** `app/services/vlm_strip_forces.py:266` — `compute_vlm_strip_forces`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Dead accumulator; nothing to source. If it were returned, Anderson §5.3 (L = integral of L'(y) dy) would cover it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Dead accumulator: total_lift is summed but never returned or read anywhere (ADR 0021 — complete but unreachable).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:247,266`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
