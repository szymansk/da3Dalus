---
name: ss-prop-pd
symbol: prop_pd
kind: parameter
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Propeller pitch-to-diameter ratio

**Definition.** Pitch over diameter of the intended propeller, converting top speed into a target RPM.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.65`

**Formula — as the code writes it.**

```
rpm_target = (v_top_mps / (prop_d * prop_pd)) * 60.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:75` — `SolutionSpaceAssumptions.prop_pd`

**Consumed by.**

- in this graph: `Target propeller RPM`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:158` · `app/services/powertrain_solution_space_service.py:393`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 1, pp. 8-9 (Pitch-to-Diameter Ratio by Mission Type): 3D aerobatic ~ 1:0.5; Scale/realistic ~ 1:0.6-0.7; Glider/electric sailplane ~ 1:0.7-0.9. Pitch itself defined in Ch. 1, pp. 6-7 as the no-slip advance per revolution.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P/D by mission: 3D ~ 0.5, Scale/trainer ~ 0.6-0.7, Glider ~ 0.7-0.9
```

**⚠️ Divergence from the source.** Three of the four values in the code's field description are supported: 3D = 0.5 matches exactly, trainer = 0.65 is the midpoint of the scale/realistic 0.6-0.7 band, glider = 0.8 is the midpoint of 0.7-0.9. The fourth, speed = 1.0, is NOT in the source, which stops at 0.9 for the steepest-pitch mission it covers. The source also gives the rationale the code omits: low P/D favours throttle response and resists blade separation at low airspeed, high P/D favours speed and endurance.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The per-mission table in the description is the closest thing to guidance anywhere in this cluster, and it carries no source (ADR 0023). The default 0.65 also collides numerically with eta_prop_lo = 0.65 and DEFAULT_ETA_PROP = 0.65, three unrelated quantities sharing a value.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Prop pitch/diameter ratio. Trainer: 0.65, 3D: 0.5, glider: 0.8, speed: 1.0" — NO_SOURCE_FOUND for the four mission values`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
