---
name: ws_sweep_max
symbol: W/S_max
kind: constant
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# W/S sweep upper bound

**Definition.** Upper bound of the wing-loading axis of the matching chart.

**Value.** `1500.0`

**Formula — as the code writes it.**

```
_WS_MAX: float = 1500.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:72` — `_WS_MAX`

**Consumed by.**

- in this graph: [[ws_range_mc|W/S sweep vector]]
- outside it: `ws_range:838`

**Source.** 🔴 NO SOURCE FOUND

> Sadraey §4.3.1 step 2 suggests 5-100 lb/ft^2 (240-4790 N/m^2) for the manned classes it addresses. 1500 N/m^2 is inside that transport-scale window and outside anything relevant here.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Confirms the inventory anomaly: a 0.5-15 kg model sits at roughly 20-150 N/m^2, so the entire RC design space is squeezed into the leftmost ~10% of the axis.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Direct ADR 0023 finding - the axis range is inherited from transport-category sizing guidance. An RC/UAV-appropriate sweep is roughly 20-200 N/m^2.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** 1500 N/m² is airliner territory; a 0.5–15 kg model sits at 20–150 N/m², so the RC design point is squeezed into the leftmost 10% of the chart (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# N/m² — upper bound`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
