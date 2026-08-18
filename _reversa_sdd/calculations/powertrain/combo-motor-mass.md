---
name: combo-motor-mass
symbol: motor_mass_kg
kind: quantity
unit: kg
cluster: powertrain
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Motor mass

**Definition.** Motor mass from the catalog, converted grams to kilograms; a missing mass becomes zero.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
motor_mass_kg = (motor.mass_g or 0) / 1000.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:212` — `_evaluate_motor_battery_combo`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Combo total mass`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:233`

**Source.** 🟡 PARTIAL

> Sadraey (2013), §8.7 (unconventional engines / electric propulsion) gives the only mass figures found for this class: 'A typical 2-hp electric motor weighs about 300 g. Operating it for 15 minutes requires about 400 g of battery.' No source prescribes how to handle a missing catalog mass.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey §8.7: 2-hp electric motor ~300 g; 400 g of battery for 15 min at that power
```

**⚠️ Divergence from the source.** Substituting 0 kg for a missing catalog mass has no source and is not neutral: Sadraey's own comparison in §8.7 turns on motor+battery mass being comparable to engine+fuel mass, so zeroing it removes the term the source treats as decisive.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A catalog row with NULL mass silently contributes 0 kg, understating total mass and overstating flight time, with no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
