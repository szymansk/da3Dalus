---
name: prt-v-bin-half-width
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# V-bin half-width fraction

**Definition.** Fraction of the gap to the adjacent anchor used to extend the outermost V-bands.

**Value.** `0.5`

**Formula — as the code writes it.**

```
_V_BIN_HALF_WIDTH_FRACTION: float = 0.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:56` — `_V_BIN_HALF_WIDTH_FRACTION`

**Consumed by.**

- in this graph: [[prt-band-boundaries|V-band lower/upper bounds]]
- outside it: `_band_boundaries:239` · `_band_boundaries:245`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Numerical binning choice; no domain source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `v_lo = max(0.0, v_sorted[0] - gap * _V_BIN_HALF_WIDTH_FRACTION)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
