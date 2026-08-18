---
name: margin-high-threshold
symbol: —
kind: parameter
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Nose-heavy static margin threshold

**Definition.** Static margin above which a 'very nose-heavy trim' warning is emitted.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.30`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:394` — `compute_enrichment`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:512`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source names 0.30 as a nose-heavy threshold. Sadraey §6.7.1 puts the 'excessive stability, sluggish' onset at >0.12; rcplanedesigner.com's largest RC mission maximum is 0.15 (Trainer). Fourth independent copy of the 0.30 constant in this cluster, and it disagrees with sm_sizing_service._SM_HEAVY_NOSE_WARN = 0.20 for the same concept.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fourth independent copy of the 0.30 SM constant (notes F3). Also disagrees with sm_sizing_service._SM_HEAVY_NOSE_WARN = 0.20 for the same concept.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
