---
name: base-mass-kg
symbol: m
kind: quantity
unit: kg
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Effective design mass

**Definition.** Design mass read from the 'mass' design assumption, used as the base speed-polar curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
base_mass = float(get_effective_assumption_value(db, aeroplane_uuid, "mass"))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:617` — `_build_speed_polar`

**Consumed by.**

- in this graph: `Speed-polar mass set`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `SpeedPolar.base_mass_kg`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.6.2 Eq. 5.30 (m_MTO/S_W = C_L·q/g); Sadraey §4.3.2 Eq. 4.30 (L = W)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
L = m_MTO · g
```

**⚠️ Divergence from the source.** Sourced as a concept (design mass sets the weight in the lift balance); the DB lookup itself is plumbing.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
