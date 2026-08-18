---
name: lfop-g
symbol: g
kind: constant
unit: m/s²
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: physical-constant
tags:
  - cluster/aero-strips
  - class/physical-constant
  - source/sourced
  - flag/physical
---

# Gravitational acceleration

**Definition.** Standard gravity used to convert mass into weight.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: gravity.*

**Value.** `9.80665`

**Formula — as the code writes it.**

```
g = 9.80665
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:487` — `_resolve_level_flight_op`

**Consumed by.**

- in this graph: `Level-flight target lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Standard gravity g_n, 3rd CGPM (1901); ISO 80000-3
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
g_n = 9.80665 m/s^2 (exact by definition)
```

**Cited in the code itself.** `app/services/section_aoa_service.py:487`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
