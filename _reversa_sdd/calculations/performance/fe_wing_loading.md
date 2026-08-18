---
name: fe_wing_loading
symbol: W/S
kind: quantity
unit: N/m^2
cluster: perf-envelope
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Wing loading (gust path)

**Definition.** Weight per reference area used in the gust mass ratio and load increment.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
wing_loading = mass_kg * g / s_ref
```

**Inputs.**

- [[fe_mass|Design mass (envelope)]]  — *⤵ fallback*
- [[fe_wing_area|Reference wing area]]  — *× unit*
- [[fe_gravity|Gravitational acceleration (flight envelope)]]

**Produced by.** `app/services/flight_envelope_service.py:88` — `_compute_mu_g`

**Consumed by.**

- in this graph: `Gust load-factor increment` · `Gust mass ratio`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Definitional. Scholz, Flugzeugentwurf 07_WingDesign §7.3 uses W/S in exactly this gust-response role.
>
> — via `scholz`

**The source states it as.**

```
W/S = m*g/S
```

**⚠️ Divergence from the source.** Three producers of a user-visible W/S with two different g (fe:88, fe:135, mkpi:273). ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Computed twice (lines 88 and 135) and a third time in mission_kpi_service._kpi_wing_loading with g=9.81 vs 9.81 here — the mission-KPI W/S is the user-visible one, so two producers of a displayed number (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
