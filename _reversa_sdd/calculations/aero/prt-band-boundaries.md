---
name: prt-band-boundaries
symbol: [V_lo, V_hi]
kind: quantity
unit: m/s
cluster: aero-polars
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/divergence
---

# V-band lower/upper bounds

**Definition.** Non-overlapping velocity window assigned to each anchor for rebinning the fine sweep.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_lo = (v_sorted[idx - 1] + v_sorted[idx]) / 2.0 ; v_hi = (v_sorted[idx] + v_sorted[idx + 1]) / 2.0
```

**Inputs.**

- [[prt-v-bin-half-width|V-bin half-width fraction]]

**Produced by.** `app/services/polar_re_table_service.py:248` — `_band_boundaries`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `build_re_table:478`

**Source.** 🟡 PARTIAL

> Standard 1-D nearest-neighbour (Voronoi) partition — midpoints between adjacent anchors

**⚠️ Divergence from the source.** Method is elementary and uncontroversial; the outermost-band extension by half the adjacent gap is an arbitrary closure with no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `v_lo = (v_sorted[idx - 1] + v_sorted[idx]) / 2.0
v_hi = (v_sorted[idx] + v_sorted[idx + 1]) / 2.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
