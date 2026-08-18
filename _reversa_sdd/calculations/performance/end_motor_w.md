---
name: end_motor_w
symbol: P_motor
kind: parameter
unit: W
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/perf-envelope
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/scale
---

# Motor continuous power

**Definition.** Continuous motor power rating; 0.0 means 'not configured'.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `default 0.0 -> None`

**Formula — as the code writes it.**

```
motor_w_val = float(_motor_w_raw) if (_motor_w_raw is not None and _motor_w_raw > 0.0) else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:549` — `compute_endurance_for_aeroplane`

**Consumed by.**

- in this graph: `Power margin`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> User-supplied continuous motor rating; 0.0 correctly mapped to None.
>
> — via `rc`

**⚠️ Scale (ADR 0023).** Compared against P_req at V_md only — see end_p_margin.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
