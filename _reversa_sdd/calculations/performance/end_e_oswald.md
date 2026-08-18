---
name: end_e_oswald
symbol: e
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
---

# Resolved Oswald efficiency

**Definition.** Cached polar Oswald factor, else the 0.8 fallback.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
e_oswald: float = e_oswald_raw if e_oswald_raw is not None else FALLBACK_E_OSWALD
```

**Inputs.**

- [[end_fallback_e|Oswald fallback]]  — *⤵ fallback*

**Produced by.** `app/services/endurance_service.py:301` — `compute_endurance`

**Consumed by.**

- in this graph: `Induced-drag factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Fitted value when available; otherwise inherits end_fallback_e (0.8, transport/GA bands only).
>
> — via `aero`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
