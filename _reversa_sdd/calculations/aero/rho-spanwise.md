---
name: rho-spanwise
symbol: ρ
kind: quantity
unit: kg/m³
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
---

# Air density (spanwise loads)

**Definition.** Density from the AeroSandbox atmosphere at the resolved operating-point altitude.

**Formula — as the code writes it.**

```
rho = float(atmosphere.density())
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2052` — `analyze_airplane_spanwise_loads`

**Consumed by.**

- in this graph: [[q-dyn|Dynamic pressure]]

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
