---
name: prt-min-samples-per-band
symbol: —
kind: parameter
unit: count
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Minimum samples per V-band / per OLS window

**Definition.** Minimum number of sweep points required before a band is fitted rather than falling back.

**Value.** `6`

**Formula — as the code writes it.**

```
_MIN_SAMPLES_PER_BAND: int = 6
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:52` — `_MIN_SAMPLES_PER_BAND`

**Consumed by.**

- in this graph: [[prt-top-band-fallback|top_band_fallback flag (in build_re_table)]]
- outside it: `_fit_polar_ols:347` · `build_re_table:482`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 6 is an unsourced sample-count floor, and one constant gates two unrelated windows (CL window at :347, V window at :482).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** One constant gates two different things: samples inside the CL window (line 347) and samples inside the V window (line 482).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `if len(cl_win) < _MIN_SAMPLES_PER_BAND:`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
