---
name: mkpi_soll_field_score
symbol: 1.0
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Soll field-friendliness score

**Definition.** Target polygon's field axis is pinned to full score by construction.

**Value.** `1.0`

**Formula — as the code writes it.**

```
"field_friendliness": 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:385` — `_objective_target_scores`

**Consumed by.**

- outside it: `MissionRadarChart.tsx Soll polygon`

**Source.** 🟢 SOURCED

> Internally consistent and correctly documented in-code: the Soll polygon represents the user's declared target, so meeting the declared field length is full score by definition.
>
> — via `scholz`

**The source states it as.**

```
1.0 by construction
```

**⚠️ Divergence from the source.** None — the reasoning is stated and sound.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Meeting the user's declared target field length is therefore full score by construction (1.0) — the Ist polygon shows how close the aircraft actually gets."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
