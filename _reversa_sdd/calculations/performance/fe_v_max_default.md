---
name: fe_v_max_default
symbol: V_max,default
kind: constant
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default maximum level speed

**Definition.** Fallback maximum level speed when the flight profile declares no goal.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `28.0`

**Formula — as the code writes it.**

```
return 28.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:586` — `_get_v_max`

**Consumed by.**

- in this graph: `Maximum level speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> 28.0 m/s is not attributable to any consulted source.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** ADR 0020, most consequential undeclared fallback in the file: it propagates into V_D, the whole velocity sweep, the gust schedule and two KPIs. A user with no flight profile receives a complete, confident V-n diagram built on an invented speed, presented with no warning. Declared twice (fe:285 signature default, fe:586 _get_v_max) so the two can drift apart.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number declared twice: as the compute_vn_curve signature default (line 285, `v_max_mps: float = 28.0`) and again as the _get_v_max fallback. Undeclared fallback — a user with no flight profile gets a full V-n diagram and dive speed built on an invented 28 m/s with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
