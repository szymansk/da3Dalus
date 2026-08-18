---
name: beta_trimmed
symbol: β
kind: quantity
unit: rad (stored) / deg (solved)
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
---

# Trimmed sideslip angle

**Definition.** Final solved sideslip angle, stored in radians.

**Formula — as the code writes it.**

```
beta_rad=math.radians(best_beta)
```

**Inputs.** [[beta_candidates|Sideslip candidate list]]

**Produced by.** `app/services/operating_point_generator_service.py:991` — `_trim_or_estimate_point`

**Consumed by.**

- in this graph: [[aero_coefficients_at_trim|Aero coefficients at the trimmed point]] · [[warn_beta_limit_reached|BETA_LIMIT_REACHED warning]]
- outside it: `app/models/analysismodels.py (beta column)` · `frontend/components/workbench/OperatingPointsPanel.tsx`

**Source.** 🟢 SOURCED

> AeroSandbox 4.2 OperatingPoint: 'beta = degrees, sideslip'. ASB also carries a documented beta sign-convention correction (operating-point beta sign convention).
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Same deg/rad split as alpha_trimmed. Additional risk: the ASB beta sign convention is version-sensitive and the code does not pin or assert it, so the stored sign of sideslip depends on the ASB release.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
