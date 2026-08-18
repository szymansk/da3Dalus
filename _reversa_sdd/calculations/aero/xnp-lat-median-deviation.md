---
name: xnp-lat-median-deviation
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

# Xnp_lat outlier deviation

**Definition.** Absolute deviation of Xnp_lat from its median; the argmax is labelled as an outlier.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
median_lat = float(np.nanmedian(lat_curve)); deviation_lat = np.abs(lat_curve - median_lat); outlier_idx = int(np.nanargmax(deviation_lat))
```

**Inputs.**

- [[xnp-lat-values|Lateral neutral point array]]

**Produced by.** `app/services/analysis_service.py:1218` — `_collect_xnp_lat_labels`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `alpha-sweep PNG panel 5`

**Source.** 🔴 NO SOURCE FOUND

> Same as xnp-median-deviation; additionally Xnp_lat itself has no textbook definition (see xnp-lat-values).
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Unconditional label, same as xnp-median-deviation; also German UI text 'Ausreißer' in an English-only frontend convention.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
