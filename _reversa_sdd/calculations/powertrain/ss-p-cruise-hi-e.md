---
name: ss-p-cruise-hi-e
symbol: p_cruise_hi_e
kind: quantity
unit: W
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
---

# Electrical cruise power at high prop efficiency

**Definition.** Cruise power at the optimistic end of the efficiency band — the lower power number.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_cruise_hi_e = _p_elec(p_aero_cruise, assumptions.eta_prop_hi, assumptions.eta_motor, assumptions.eta_esc)
```

**Inputs.**

- [[ss-p-elec|Electrical power required]]
- [[ss-p-aero-cruise|Aerodynamic power at cruise]]
- [[ss-eta-prop-hi|Propeller efficiency band upper bound]]  — *⊣ limit*
- [[ss-eta-motor|Motor efficiency (solution space)]]
- [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:367` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Mission energy at high prop efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:412` · `app/services/powertrain_solution_space_service.py:436`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15. The high-efficiency endpoint used (0.78) exceeds the cited RC-scale plateau — see ss-eta-prop-hi.
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
P_elec = P_aero / eta_total
```

**⚠️ Divergence from the source.** The optimistic branch is computed with eta_prop_hi = 0.78, which Deters/Ananda/Selig (2014) §VI places above the 0.60-0.70 plateau for small-scale low-Re propellers, so this branch understates cruise power at RC scale.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
