---
name: cdftp-delta-cd
symbol: delta_cd
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Section drag delta (installed turbulator)

**Definition.** Per-section drag change from the turbulator at its current position.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_cd=cd_tripped - cd_clean,
```

**Inputs.**

- [[cdftp-cd-tripped|Tripped section drag (installed-turbulator path)]]
- [[cdftp-cd-clean|Clean section drag (installed-turbulator path)]]

**Produced by.** `app/services/turbulator_optimizer_service.py:717` — `compute_delta_cd0_from_turbulator_position`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Installed-turbulator 3D drag increment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.12-4.12.3 (profile drag as a function of transition location)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
delta_cd = cd(x_tr installed) - cd(x_tr natural)
```

**⚠️ Divergence from the source.** Same well-founded definition as tos-delta-cd, evaluated at the installed rather than the optimal trip position.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:717`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
