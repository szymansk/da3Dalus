---
name: cm-strip-colors
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Cm-gradient stability colours

**Definition.** Per-point stability colour derived from the local dCm/dalpha gradient.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if g < -0.01: "#4caf50"  # stable / elif g <= 0.01: "#ffb74d"  # marginal / else "#e57373"  # unstable
```

**Inputs.**

- [[cm-gradient|Local Cm gradient]]
- [[stability-slope-thresholds|Stability classification thresholds]]  — *⊣ limit*

**Produced by.** `app/services/analysis_service.py:1037` — `_compute_cm_strip_colors`

**Consumed by.**

- outside it: `_plot_cm_stability trend strips`

**Source.** 🟡 PARTIAL

> Same as stability-slope-thresholds: sign criterion from Sadraey §11.6.2 Eq. 11.17; ±0.01 literals unsourced.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Second producer of the stable/marginal/unstable verdict with the literals copied rather than shared (ADR 0022); inherits the same over-wide dead-band defect.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023: unvalidated at 0.5–15 kg.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Second producer of the stable/neutral/unstable verdict (see stability-slope-thresholds) with the same literals copied instead of shared.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
