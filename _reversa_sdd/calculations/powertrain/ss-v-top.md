---
name: ss-v-top
symbol: V_top
kind: quantity
unit: m/s
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - flag/scale
---

# Top speed used for peak sizing

**Definition.** The speed at which peak power, peak current, ESC rating and KV are sized. User-supplied or derived from cruise. Must exceed cruise or the request is rejected.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_top_mps = assumptions.v_top_mps ; if v_top_mps is None: v_top_mps = v_cruise_mps * 1.4 ; if v_top_mps <= v_cruise_mps: raise ValidationDomainError(...)
```

**Inputs.**

- [[ss-v-cruise|Cruise speed (solution space)]]
- [[ss-v-top-factor|Top-speed derivation factor]]

**Produced by.** `app/services/powertrain_solution_space_service.py:334` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aerodynamic power at top speed` · `Target propeller RPM`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:350` · `app/services/powertrain_solution_space_service.py:392` · `app/services/powertrain_solution_space_service.py:158` · `frontend/components/workbench/PowertrainTab.tsx:1145`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eq. 4.56 — V_max is the sizing speed for the power-loading constraint, and §4.6 inputs give V_max ~ 1.2-1.3 V_C when not specified directly.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
(W/P)_Vmax = eta_P / [rho_o V_max^3 C_Do/(2(W/S)) + (2K/(rho sigma V_max))(W/S)]  (Eq. 4.56)
```

**⚠️ Divergence from the source.** Using V_top as the peak-power sizing point matches Sadraey exactly. The derived default (1.4 x V_cruise) does not — see ss-v-top-factor.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** See ss-v-top-factor: the 1.2-1.3 source band is transport-derived.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `schema field description: "Top speed [m/s] for peak-power sizing. Defaults to 1.4 × V_cruise when not supplied."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
