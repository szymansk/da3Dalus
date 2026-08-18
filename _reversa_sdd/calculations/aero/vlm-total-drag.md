---
name: vlm-total-drag
symbol: total_drag
kind: quantity
unit: N
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Accumulated total drag

**Definition.** Running sum of all strip drags over the whole airplane.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
total_drag += drag
```

**Inputs.**

- [[vlm-strip-drag|Strip drag force]]

**Produced by.** `app/services/vlm_strip_forces.py:267` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Dead accumulator; nothing to source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Dead accumulator: total_drag is summed but never returned or read anywhere (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:248,267`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
