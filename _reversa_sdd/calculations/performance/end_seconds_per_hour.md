---
name: end_seconds_per_hour
symbol: 3600
kind: constant
unit: s/h
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
---

# Wh-to-Ws conversion

**Definition.** Seconds per hour converting battery capacity in Wh to joules.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3600.0`

**Formula — as the code writes it.**

```
(capacity_wh_val * 3600.0) / p_req_vmin
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:403` — `compute_endurance`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Flight time at V_md` · `Maximum endurance`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> SI unit conversion.
>
> — via `scholz`

**The source states it as.**

```
3600 s/h
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
