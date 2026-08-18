---
name: neutral-strip-percentiles
kind: constant
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Neutral-trend percentile thresholds

**Definition.** Self-referential percentile cut-offs colouring the neutral-point trend strip.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `50 / 85`

**Formula — as the code writes it.**

```
low_thr = float(np.percentile(valid, 50)); high_thr = float(np.percentile(valid, 85))
```

**Inputs.**

- [[neutral-combined-metric|Neutral-point sensitivity metric]]

**Produced by.** `app/services/analysis_service.py:1257` — `_compute_neutral_strip_colors`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `alpha-sweep PNG panel 5 trend strip`

**Source.** 🔴 NO SOURCE FOUND

> 50th/85th percentiles are self-referential thresholds — 15% of every sweep is always coloured 'critical' regardless of how flat the curve is. No source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Relative thresholds: 15% of every sweep is always coloured 'critical' regardless of how flat the curve is; NO_SOURCE_FOUND.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
