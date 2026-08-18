---
name: end_k_induced
symbol: k
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Induced-drag factor

**Definition.** Lift-dependent drag coefficient factor of the parabolic polar.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
k = 1.0 / (math.pi * e * ar)
```

**Inputs.**

- [[end_e_oswald|Resolved Oswald efficiency]]  — *⤵ fallback*

**Produced by.** `app/services/endurance_service.py:121` — `_power_required`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Total drag coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e §6.7.2 (airplane drag polar); Scholz, Flugzeugentwurf 05_PreliminarySizing §5.7.
>
> — via `aero, scholz`

**The source states it as.**

```
k = 1/(pi*e*AR)
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
