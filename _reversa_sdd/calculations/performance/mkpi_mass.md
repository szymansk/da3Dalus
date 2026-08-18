---
name: mkpi_mass
symbol: m
kind: parameter
unit: kg
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: user-input
tags:
  - cluster/perf-envelope
  - class/user-input
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Mass for wing loading

**Definition.** Mass from the cached context, falling back to the aeroplane's total_mass_kg column.

**User input.** Supplied from outside the calculation (assumption store or request), not derived.

**Formula — as the code writes it.**

```
mass = ctx.get("mass_kg"); if not isinstance(mass, (int, float)) or mass <= 0: mass = aeroplane.total_mass_kg if aeroplane.total_mass_kg else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:452` — `compute_mission_kpis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `KPI: wing loading`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> ctx mass_kg with a fallback to the aeroplane's total_mass_kg column — both user-owned values.
>
> — via `rc`

**⚠️ Divergence from the source.** Fallback is between two legitimate user sources rather than to an invented constant, so it is benign — but it is still undeclared, and the two can differ.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
