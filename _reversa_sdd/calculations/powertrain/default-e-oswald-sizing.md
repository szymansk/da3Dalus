---
name: default-e-oswald-sizing
symbol: _DEFAULT_E_OSWALD
kind: constant
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Default Oswald efficiency (sizing)

**Definition.** RC-typical Oswald span efficiency used when neither request nor context supplies e.

**Value.** `0.8`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:45` — `_DEFAULT_E_OSWALD`

**Consumed by.**

- in this graph: [[resolved-e-oswald|Resolved Oswald efficiency]]
- outside it: `app/services/powertrain_sizing_service.py:177`

**Source.** 🟢 SOURCED

> Anderson, J.D., Fundamentals of Aerodynamics, 6th ed., §6.7.2 (Airplane Drag Polar and Oswald Efficiency Factor): 'Typical airplanes: e = 0.70 to 0.85; high-efficiency aircraft can approach e = 0.90.' Also Scholz exam material (HAW Hamburg Klausur SS19, §1.6): cruise clean e = 0.85-0.92, takeoff/landing e = 0.70-0.75.
>
> — via `aerodynamics-expert / aircraft-design-scholz`

**The source states it as.**

```
C_D = C_D,0 + C_L^2/(pi * e_tilde * AR),  e_tilde = 1/(1 + r pi e AR)
```

**⚠️ Divergence from the source.** 0.8 falls inside Anderson's 0.70-0.85 typical band, so the value is consistent. Note the two sources disagree with each other on the cruise band (Anderson 0.70-0.85 overall vs Scholz 0.85-0.92 clean cruise) because Anderson's Oswald factor absorbs the C_L-dependent parasite term and Scholz's does not.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Anderson's 0.70-0.85 and Scholz's 0.85-0.92 are both full-size-airplane bands. No RC-scale Oswald value was found in the rc-aircraft-designer vault; Anderson explicitly warns his companion Raymer correlation e = 1.78(1 - 0.045 AR^0.68) - 0.64 'applies only to conventional aspect ratios'. Adopting 0.8 at 0.5-15 kg scale is unvalidated at that scale.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Conflicts with the solution space's own fallback of 0.75 for the same quantity (powertrain_solution_space_service.py:285) and with endurance_service.py:57 FALLBACK_E_OSWALD = 0.8 — three fallback values, two of them different.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
