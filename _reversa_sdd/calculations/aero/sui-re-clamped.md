---
name: sui-re-clamped
symbol: Re_clamped
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
---

# Grid-clamped Reynolds + clamp flag

**Definition.** Query Re clamped to the low-Re grid endpoints, with a flag when clamping occurred.

**Formula — as the code writes it.**

```
if re <= grid[0]:
    return float(grid[0]), True
if re >= grid[-1]:
    return float(grid[-1]), True
return re, False
```

**Inputs.** [[sui-re-root|Root-chord Reynolds number]] · [[low-re-grid|Absolute low-Re grid]]

**Produced by.** `app/services/suitability_service.py:128` — `_clamp_re_to_grid`

**Consumed by.**

- outside it: `search_suitability:260,384` · `SuitabilityQuery.reynolds / re_clamped:688-689` · `interpolate_polar_at_re:447`

**Source.** 🟡 PARTIAL

> Sharpe (2024), §7.2.4 — analysis_confidence structurally decays under extrapolation, so clamping to the sampled grid rather than extrapolating is the behaviour the surrogate's own UQ design implies
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Clamping is the defensible choice; no source prescribes it here and none is cited. Boundary bug: re == grid[0] or grid[-1] is reported as clamped although nothing was clamped, so exact-endpoint queries carry a spurious caveat.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Exact-endpoint queries (re == grid[0]) are reported as clamped although no clamping occurred.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `if re <= grid[0]:
    return float(grid[0]), True`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
