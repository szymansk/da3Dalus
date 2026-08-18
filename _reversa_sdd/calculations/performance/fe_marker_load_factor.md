---
name: fe_marker_load_factor
symbol: n_op
kind: constant
unit: g
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Operating-point marker load factor

**Definition.** Load factor assigned to every operating-point marker on the V-n diagram.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
n = 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:606` — `_load_operating_point_markers`

**Consumed by.**

- in this graph: `KPI: max load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `VnDiagram.tsx markers`

**Source.** 🟢 SOURCED

> Definitional for steady level flight; the docstring's reasoning is correct.
>
> — via `aero`

**The source states it as.**

```
n = 1.0 in level flight (L = W)
```

**⚠️ Divergence from the source.** The constant is right, its consumer is wrong. Hardcoded n=1.0 flows into kpi_max_load_factor, so an operating point named 'max_turn' would report 1.0 g under the label 'Max Load Factor' with confidence 'trimmed'. Also _load_operating_point_markers accepts mass_kg and wing_area_m2 (fe:592-593) and uses neither — dead parameters from the abandoned CL-based derivation (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Hardcoded n=1.0 flows into the max_load_factor KPI: if an operating point is named 'max_turn', the KPI reports 1.0 g labelled 'Max Load Factor' with confidence 'trimmed'. Name contradicts value. Additionally _load_operating_point_markers takes mass_kg and wing_area_m2 (lines 592-593) and never uses them — dead parameters left from the abandoned CL-based derivation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Operating points represent level flight conditions (n=1.0). Without stored CL, we cannot derive actual load factor."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
