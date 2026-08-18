---
name: alr-cl-valid-range
symbol: [CL_lo, CL_hi]
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Polar-fit validity CL range

**Definition.** CL span covered by trusted data, stored as the parabolic fit's validity window.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
result["cl_valid_lo"] = float(np.min(cl_f))
result["cl_valid_hi"] = float(np.max(cl_f))
```

**Inputs.**

- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*
- [[alr-confidence-gate|NeuralFoil confidence gate]]

**Produced by.** `app/services/airfoil_low_re_service.py:673` — `_extract_metrics`

**Consumed by.**

- outside it: `AirfoilLowRePolarModel.cl_valid_lo/hi` · `_row_to_dict:369`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Implementation bookkeeping, no domain source. Worse, it has no consumer: score_target_cl evaluates the parabola at cl_target without consulting cl_valid_lo/hi, so the recorded validity window never constrains extrapolation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer: score_target_cl evaluates CD at cl_target without ever checking cl_valid_lo/hi, so the stored validity range never constrains extrapolation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Validity range: CL where parabolic fit error is acceptable
# Use the entire range with trusted data as validity range
result["cl_valid_lo"] = float(np.min(cl_f))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
