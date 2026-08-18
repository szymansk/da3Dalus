---
name: combo-total-mass
symbol: total_mass
kind: quantity
unit: kg
cluster: powertrain
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Combo total mass

**Definition.** All-up mass for this combo: user-supplied airframe mass plus motor and battery masses. No ESC, no propeller, no receiver.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
total_mass = request.airframe_mass_kg + motor_mass_kg + battery_mass_kg
```

**Inputs.**

- [[combo-motor-mass|Motor mass]]
- [[combo-battery-mass|Battery mass]]

**Produced by.** `app/services/powertrain_sizing_service.py:233` — `_evaluate_motor_battery_combo`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Estimated cruise power` · `Power required for a motor+battery combo`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:242`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Sadraey (2013) §8.7 defines the electric propulsion SYSTEM as 'an electric motor, battery, and propeller'. The code's total mass omits the propeller entirely and also omits the ESC that it goes on to select, so the mass driving the induced-drag term is systematically light against the source's own system definition.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The ESC is matched later (line 259) but its mass is never added, and the propeller is never selected at all — the mass that drives the induced-drag term is systematically light.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
