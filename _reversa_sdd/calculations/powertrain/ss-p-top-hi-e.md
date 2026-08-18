---
name: ss-p-top-hi-e
symbol: p_top_hi_e
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
  - flag/scale
---

# Electrical peak power at high prop efficiency

**Definition.** Peak power at the optimistic end of the efficiency band.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_top_hi_e = _p_elec(p_aero_top, assumptions.eta_prop_hi, assumptions.eta_motor, assumptions.eta_esc)
```

**Inputs.**

- [[ss-p-elec|Electrical power required]]
- [[ss-p-aero-top|Aerodynamic power at top speed]]
- [[ss-eta-prop-hi|Propeller efficiency band upper bound]]  — *⊣ limit*
- [[ss-eta-motor|Motor efficiency (solution space)]]
- [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:372` — `compute_solution_space`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:410` · `app/services/powertrain_solution_space_service.py:438`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15 applied at V_top.
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
P_elec(V_top) = P_aero(V_top) / eta_total
```

**⚠️ Divergence from the source.** Uses eta_prop_hi = 0.78, above the 0.60-0.70 small-scale plateau documented by Deters/Ananda/Selig (2014) §VI, so the optimistic peak-power figure is optimistic beyond what the RC-scale measurements support.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Inherits the transport-derived V_top ratio — see ss-v-top-factor.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
