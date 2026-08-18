---
name: mkpi_field_score
symbol: score_field
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Field-friendliness score

**Definition.** Achievement ratio of the declared target field length to the computed one, clipped to [0,1].

**Formula — as the code writes it.**

```
score = max(0.0, min(1.0, target_field_length_m / eff))
```

**Inputs.** [[mkpi_target_field_length|Target field length]] · [[mkpi_effective_field_length|Effective field length]]

**Produced by.** `app/services/mission_kpi_service.py:327` — `_compute_field_length_score`

**Consumed by.**

- in this graph: [[mkpi_field_friendliness|KPI: field friendliness]]

**Source.** 🔴 NO SOURCE FOUND

> Achievement-ratio construction with no external source; distinct from every other axis.
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
score = clip(target/effective, 0, 1)
```

**⚠️ Divergence from the source.** This axis is scored on a different scale from the other six — it bypasses _normalise_score and range_min/range_max entirely, yet the response still ships range_min/range_max for it (mkpi:343-351). AxisDrawer will display bounds that played no part in the score.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** This axis is scored on a different scale from the other six: it bypasses _normalise_score and range_min/range_max entirely, yet the response still ships range_min/range_max for it (line 343-351) — values the AxisDrawer will show but that played no part in the score.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
