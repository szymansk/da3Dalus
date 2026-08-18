---
name: xnp-median-deviation
kind: quantity
unit: m
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Xnp outlier deviation

**Definition.** Absolute deviation of Xnp from its median, whose argmax is flagged as an outlier.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
median_xnp = float(np.nanmedian(xnp_curve)); deviation = np.abs(xnp_curve - median_xnp); outlier_idx = int(np.nanargmax(deviation))
```

**Inputs.**

- [[xnp-values|Longitudinal neutral point array]]

**Produced by.** `app/services/analysis_service.py:1188` — `_collect_xnp_outlier_labels`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `alpha-sweep PNG panel 5`

**Source.** 🔴 NO SOURCE FOUND

> Median-absolute-deviation outlier labelling of Xnp has no aerodynamic source. No threshold is applied, so the label 'Xnp Ausreißer?' fires on every sweep including a perfectly flat curve.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** There is no threshold — the largest deviation is ALWAYS labelled 'Xnp Ausreißer?' even on a perfectly flat curve.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
