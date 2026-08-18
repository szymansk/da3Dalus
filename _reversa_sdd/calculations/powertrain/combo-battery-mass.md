---
name: combo-battery-mass
symbol: battery_mass_kg
kind: quantity
unit: kg
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Battery mass

**Definition.** Battery mass from the catalog, grams to kilograms; a missing mass becomes zero.

**Formula — as the code writes it.**

```
battery_mass_kg = (battery.mass_g or 0) / 1000.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:213` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: [[combo-total-mass|Combo total mass]]
- outside it: `app/services/powertrain_sizing_service.py:233`

**Source.** 🟡 PARTIAL

> Sadraey (2013), §8.7: 'Operating [a 2-hp electric motor] for 15 minutes requires about 400 g of battery ... The electric system therefore weighs more overall when battery + motor are compared with engine + fuel.'
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Same silent-zero substitution as combo-motor-mass, with the same consequence.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same silent-zero substitution as combo-motor-mass.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
