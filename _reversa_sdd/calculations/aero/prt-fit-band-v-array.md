---
name: prt-fit-band-v-array
symbol: —
kind: parameter
unit: m/s
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# _fit_band_with_ar v_array parameter

**Definition.** Velocity array accepted by the band fitter but never referenced in its body.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
def _fit_band_with_ar(v_array: np.ndarray, cl_array, cd_array, v_center, mac_m, rho, cl_max, ar)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:255` — `_fit_band_with_ar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Unused parameter; no quantity to source (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Unused parameter — the band fit ignores V entirely and uses only v_center.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `def _fit_band_with_ar(
    v_array: np.ndarray,`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
