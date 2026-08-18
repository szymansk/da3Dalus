---
name: constraint_category
symbol: category
kind: quantity
unit: enum
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Constraint category tag

**Definition.** Provenance label classifying each constraint as universal, RC-specific, or CS-25-only.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"category": "universal"  /  "category": "rc_specific"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:891` — `compute_chart`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `ConstraintLine.category (schemas/matching_chart.py:22)` · `frontend/hooks/useMatchingChart.ts ConstraintCategory` · `frontend MatchingChartTab.tsx badges`

**Source.** 🔴 NO SOURCE FOUND

> App-specific provenance taxonomy; no counterpart in Scholz or Sadraey.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The tag is a good ADR 0023 instrument - but it is currently miscalibrated. Constraints tagged 'universal' (Takeoff, Landing) are in fact built on GA/Cessna-fitted constants (1.66, 2.73, 0.5847), so the label asserts a scale-independence the numbers do not have. Separately, the 'cs25_only' literal exists in the schema and frontend type with no producer (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The 'cs25_only' literal is declared in the schema and the frontend type but no producer ever emits it — a value in the public contract with no source (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# The existing 5 constraints (TO / LDG / Cruise / Climb / Stall) are all tagged "universal". The CS-25-only OEI bands are not emitted by this service yet; if a future change adds them they must carry category "cs25_only" + binding_for_warning=False.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
