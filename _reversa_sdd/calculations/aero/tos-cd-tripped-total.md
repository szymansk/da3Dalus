---
name: tos-cd-tripped-total
symbol: cd_tripped
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Tripped total drag coefficient

**Definition.** Clean drag coefficient plus the 3D turbulator drag increment.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_tripped = cd_clean + delta_cd0
```

**Inputs.**

- [[tos-cd-clean-avg|Area-weighted mean clean section drag]]
- [[tos-delta-cd0|Area-weighted 3D drag increment]]

**Produced by.** `app/services/turbulator_optimizer_service.py:344` — `compute_ld_summary`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Tripped lift-to-drag ratio`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (drag decomposition and superposition of increments)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_D = C_D,baseline + delta_C_D
```

**⚠️ Divergence from the source.** Adding a drag increment to a baseline coefficient is standard PROVIDED both share a reference area. They do here for a symmetric wing (see tos-delta-cd0), so the inventory's 'different reference areas' concern does not hold in that case. It DOES hold when callers pass wing_symmetric=False: the section areas are still normalised to s_ref/2 but the factor 2 is dropped, so delta_cd0 is halved relative to cd_clean_avg.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Mixes a 2D area-weighted section cd with a 3D S_ref-normalised ΔCD0 — the two are normalised on different reference areas.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:344`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
