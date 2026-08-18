---
name: chart_warnings
symbol: warnings
kind: quantity
unit: list[str]
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Matching-chart design warnings

**Definition.** User-facing warnings emitted for defaulted Oswald factor and estimated cruise speed.

**Formula — as the code writes it.**

```
warnings.append(...)
```

**Inputs.** [[e_resolved|Resolved Oswald factor]] · [[v_cruise_resolved|Resolved cruise speed]]

**Produced by.** `app/services/matching_chart_service.py:759` — `compute_chart`

**Consumed by.**

- outside it: `MatchingChartResponse.warnings` · `frontend/hooks/useMatchingChart.ts MatchingChartData.warnings`

**Source.** 🔴 NO SOURCE FOUND

> Internal ADR 0020 policy artefact, not a physical quantity.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Only 2 of the ~8 fallbacks in this service emit a warning. cd0 = 0.03, AR = 7.0, CL_max = 1.4, unknown mode, W/S = 0 design point and the strictest-mission-min substitution are all silent. Given how many constants in this cluster are NO_SOURCE_FOUND or GA-calibrated, the warning surface is the main thing standing between the user and an unsourced number.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only 2 of the ~8 fallbacks in this service emit a warning — cd0=0.03, AR=7.0, CL_max=1.4, unknown mode, WS=0 design point and the strictest-mission-min substitution are all silent (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Oswald factor e not computed — using default 0.8. Run assumption recompute for an accurate induced-drag estimate."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
