---
name: alr-interp-re-grid-param
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# interpolate_polar_at_re re_grid parameter

**Definition.** Re grid argument required by the signature but never referenced in the body.

**Formula — as the code writes it.**

```
def interpolate_polar_at_re(polar_rows: list, re_query: float, re_grid: list[int]) -> dict | None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:307` — `interpolate_polar_at_re`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Unused parameter; compute_re_cd0_reference:806-808 imports get_settings() solely to feed it (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Unused parameter; compute_re_cd0_reference:806-808 imports get_settings() solely to fetch low_re_grid and pass it to this argument that is ignored (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `re_grid: list[int],
) -> dict \| None:`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
