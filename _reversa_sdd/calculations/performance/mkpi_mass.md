---
name: mkpi_mass
symbol: m
kind: parameter
unit: kg
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Mass for wing loading

**Definition.** Mass from the cached context, falling back to the aeroplane's total_mass_kg column.

**Formula — as the code writes it.**

```
mass = ctx.get("mass_kg"); if not isinstance(mass, (int, float)) or mass <= 0: mass = aeroplane.total_mass_kg if aeroplane.total_mass_kg else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:452` — `compute_mission_kpis`

**Consumed by.**

- in this graph: [[mkpi_wing_loading|KPI: wing loading]]

**Source.** 🟢 SOURCED

> ctx mass_kg with a fallback to the aeroplane's total_mass_kg column — both user-owned values.
>
> — via `rc`

**⚠️ Divergence from the source.** Fallback is between two legitimate user sources rather than to an invented constant, so it is benign — but it is still undeclared, and the two can differ.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
