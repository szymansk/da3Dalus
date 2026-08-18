---
name: resolved-e-oswald
symbol: e
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Resolved Oswald efficiency

**Definition.** Oswald efficiency resolved by the same three-tier priority.

**Formula — as the code writes it.**

```
e_oswald = _pick(request.e_oswald, "e_oswald", _DEFAULT_E_OSWALD, "Oswald efficiency factor (e_oswald)", "e_oswald")
```

**Inputs.** [[default-e-oswald-sizing|Default Oswald efficiency (sizing)]]

**Produced by.** `app/services/powertrain_sizing_service.py:174` — `_resolve_aero_params`

**Consumed by.**

- in this graph: [[combo-cruise-power|Estimated cruise power]] · [[combo-required-power|Power required for a motor+battery combo]]
- outside it: `app/services/powertrain_sizing_service.py:246` · `app/services/powertrain_sizing_service.py:312`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2: typical airplanes e = 0.70-0.85; Scholz HAW Hamburg Klausur SS19 §1.6: cruise clean 0.85-0.92, takeoff/landing 0.70-0.75.
>
> — via `aerodynamics-expert / aircraft-design-scholz`

**The source states it as.**

```
C_D = C_D,0 + C_L^2/(pi e AR)
```

**⚠️ Scale (ADR 0023).** Both bands are full-size-airplane data. No RC-scale Oswald factor was found in the rc-aircraft-designer vault.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
