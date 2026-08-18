---
name: fe_n_points
symbol: n_points
kind: constant
unit: -
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: ANOMALY_REFUTED
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/no-source-found
  - audit/anomaly-refuted
  - flag/anomaly
  - flag/divergence
---

# V-n sampling resolution

**Definition.** Number of velocity samples on each envelope boundary.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `60`

**Formula — as the code writes it.**

```
n_points = 60  # > 50 as required
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:318` — `compute_vn_curve`

🟠 **Corrected by the audit** — the extraction claimed `ANOMALY_REFUTED`. 

**Consumed by.**

- in this graph: `Velocity sweep points`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> '# > 50 as required' refers to an internal acceptance criterion, not an external source. None needed for a plot resolution.
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Declared independently at fe:318 (maneuver) and fe:169 (gust default). Same value today, so the two polylines share an x-grid by coincidence. Changing one desynchronises the maneuver and gust curves silently — the gust-critical crossing detection then compares points at different speeds.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Declared twice with the same value but independently: line 318 for the maneuver curve and line 169 as the _build_gust_lines default. Changing one silently desynchronises the two polylines' x-grids.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"# > 50 as required"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
