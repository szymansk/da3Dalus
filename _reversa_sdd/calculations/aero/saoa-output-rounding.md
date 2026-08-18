---
name: saoa-output-rounding
symbol: —
kind: constant
unit: decimals
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Output rounding precision

**Definition.** y/chord/cl rounded to 6 decimals, all angles to 4 decimals before serialisation.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `6 / 4`

**Formula — as the code writes it.**

```
round(float(y_arr[i]), 6) … round(float(alpha_geom_arr[i]), 4)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:346` — `compute_section_aoa`

**Consumed by.**

- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaResponse`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Serialisation choice. Worth noting only that 4 decimal places on angles (1e-4 deg) implies a precision several orders finer than the model's own accuracy.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:346-352`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
