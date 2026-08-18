---
name: prt-monotonicity-tolerance
symbol: —
kind: constant
unit: dimensionless (CD)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Polar monotonicity guard tolerance

**Definition.** Negative dCD tolerance below which the band fit is rejected as non-monotonic.

**Value.** `-1e-6`

**Formula — as the code writes it.**

```
if np.any(diffs < -1e-6):
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:364` — `_fit_polar_ols`

**Consumed by.**

- outside it: `_fit_polar_ols:369 (returns None triple)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** -1e-6 is a floating-point tolerance, not a physical constant. No source needed or found.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `diffs = np.diff(cd_sorted)
if np.any(diffs < -1e-6):`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
