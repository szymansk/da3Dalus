---
name: cl_max_base_fallback_fl
symbol: CL_max
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Base CL_max fallback (field length)

**Definition.** CL_max used when the aircraft dict carries no cl_max.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.4`

**Formula — as the code writes it.**

```
cl_max_base: float = float(cl_max_raw) if cl_max_raw is not None else 1.4
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:356` — `cl_max_base`

**Consumed by.**

- in this graph: `Landing CL_max (field length)` · `Takeoff CL_max (field length)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cl_max_to:360` · `cl_max_ldg:361`

**Source.** 🟡 PARTIAL

> Sadraey 2013 Tables 4.10/4.11 by class: home-built 1.2-1.8, microlight 1.8-2.4, sailplane/glider 1.8-2.5, very light/GA light 1.6-2.2. Scholz 05_PreliminarySizing Table 5.1: single-engine propeller CL_max,TO 1.3-1.9 / CL_max,L 1.6-2.3. 1.4 falls inside the home-built band but is not attributable to any specific entry.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Silent fallback with no DesignWarning (ADR 0020), and the same literal is duplicated at matching_chart_service.py:807 and field_lengths.py:179 - three producers of one number (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** All tabulated classes are manned aircraft. No source gives CL_max for a 0.5-15 kg low-Reynolds wing, where achievable CL_max is typically lower than the manned bands suggest.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Silent 1.4 fallback with no DesignWarning (ADR 0020); the same literal is duplicated at matching_chart_service.py:807 and field_lengths.py:179.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
