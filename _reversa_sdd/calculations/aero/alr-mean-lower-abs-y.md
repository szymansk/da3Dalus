---
name: alr-mean-lower-abs-y
symbol: —
kind: quantity
unit: chord fraction
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/divergence
---

# Mean |y| of lower surface

**Definition.** Mean absolute lower-surface ordinate, the legacy flat-bottom gate.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
mean_lower_abs_y = float(np.mean(np.abs(y_lower)))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:238` — `classify_family`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Airfoil family label`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `classify_family:286`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Bespoke legacy flat-bottom gate; no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `mean_lower_abs_y = float(np.mean(np.abs(y_lower)))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
