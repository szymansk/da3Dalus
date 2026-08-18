---
name: prt-v-bin-half-width
symbol: —
kind: parameter
unit: dimensionless
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
  - flag/divergence
---

# V-bin half-width fraction

**Definition.** Fraction of the gap to the adjacent anchor used to extend the outermost V-bands.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.5`

**Formula — as the code writes it.**

```
_V_BIN_HALF_WIDTH_FRACTION: float = 0.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:56` — `_V_BIN_HALF_WIDTH_FRACTION`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `V-band lower/upper bounds`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_band_boundaries:239` · `_band_boundaries:245`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Numerical binning choice; no domain source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `v_lo = max(0.0, v_sorted[0] - gap * _V_BIN_HALF_WIDTH_FRACTION)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
