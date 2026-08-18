---
name: rho-spanwise
symbol: ρ
kind: quantity
unit: kg/m³
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Air density (spanwise loads)

**Definition.** Density from the AeroSandbox atmosphere at the resolved operating-point altitude.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rho = float(atmosphere.density())
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2052` — `analyze_airplane_spanwise_loads`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Dynamic pressure`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> AeroSandbox asb.Atmosphere — U.S. 1976 COESA/ISA; Scholz 05_PreliminarySizing §5.6.2
>
> — via `aerosandbox-expert, aircraft-design-scholz`

**The source states it as.**

```
ISA: T(h) = 288.15 − 0.0065·h [m], rho = p/(R·T)
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
