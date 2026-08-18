---
name: ss-p-top-lo-e
symbol: p_top_lo_e
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
  - flag/scale
---

# Electrical peak power at low prop efficiency

**Definition.** Peak power at the pessimistic end of the efficiency band; produces the worst-case current the UI actually shows.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_top_lo_e = _p_elec(p_aero_top, assumptions.eta_prop_lo, assumptions.eta_motor, assumptions.eta_esc)
```

**Inputs.**

- [[ss-p-elec|Electrical power required]]
- [[ss-p-aero-top|Aerodynamic power at top speed]]
- [[ss-eta-prop-lo|Propeller efficiency band lower bound]]  — *⊣ limit*
- [[ss-eta-motor|Motor efficiency (solution space)]]
- [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:369` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:398` · `app/services/powertrain_solution_space_service.py:439`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15 applied at V_top; low-band endpoint 0.65 supported by Deters/Ananda/Selig (2014) §VI and Brandt & Selig (2011) §III.
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
P_elec(V_top) = P_aero(V_top) / eta_total
```

**⚠️ Scale (ADR 0023).** Inherits the transport-derived V_top ratio — see ss-v-top-factor.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
