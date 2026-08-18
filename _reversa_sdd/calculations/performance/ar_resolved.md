---
name: ar_resolved
symbol: AR
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Resolved aspect ratio

**Definition.** Wing aspect ratio with a hardcoded fallback.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `7.0 (fallback)`

**Formula — as the code writes it.**

```
ar: float = float(aircraft.get("ar", aircraft.get("aspect_ratio", 7.0)))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:805` — `compute_chart`

**Consumed by.**

- in this graph: `Induced-drag factor` · `Climb constraint T/W` · `Cruise constraint T/W` · `Vertical-climb T/W` · `Resolved cruise speed` · `Minimum-drag speed` · `WCL-derived W/S ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `all constraint helpers` · `_wcl_constraint:1110` · `hover_text:925,940`

**Source.** 🔴 NO SOURCE FOUND

> No source for a default aspect ratio. AR is a primary design variable in both authorities (Scholz 05_PreliminarySizing; Sadraey Ch. 5), selected by mission, never defaulted.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Silent 7.0 fallback duplicated at matching_chart_service.py:794 and matching_chart.py:97 (ADR 0020 + ADR 0022). Because AR enters K = 1/(pi*e*AR), a wrong default silently distorts the cruise, climb and vertical-climb lines simultaneously.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated fallback at line 794 and at matching_chart.py:97; silent (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
