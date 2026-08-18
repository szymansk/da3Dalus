---
name: air-density-perf
symbol: rho
kind: quantity
unit: kg/m^3
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Air density at altitude (performance)

**Definition.** Air density from an isothermal exponential atmosphere with 8500 m scale height.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return RHO_SEA_LEVEL * math.exp(-altitude_m / 8500.0)
```

**Inputs.**

- [[rho-sea-level-perf|Sea-level air density (performance module)]]
- [[atmosphere-scale-height-perf|Isothermal atmosphere scale height (performance)]]
- [[request-altitude-m|Operating altitude (performance)]]

**Produced by.** `app/services/powertrain_performance.py:348` — `_air_density`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Shaft power per velocity sample` · `Thrust per velocity sample` · `Propeller absorbed torque` · `Propeller shaft power (operating-point helper)` · `Propeller thrust (operating-point helper)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:385` · `app/services/powertrain_performance.py:524` · `app/services/powertrain_performance.py:695`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz / aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey (2013) Eq. 4.94a: sigma = (1 - 6.873e-6 * h)^4.26 for 0 <= h <= 36,000 ft; Eq. 4.94b: sigma = 0.2967 exp(1.7355 - 4.8075e-5 h) for 36,000-65,000 ft. Anderson 6e §1.9: dp/dy = -rho g only.
```

**⚠️ Divergence from the source.** The code's rho = 1.225 * exp(-h/8500) matches neither authority. Sadraey's troposphere model (the only regime an RC/UAV aircraft occupies) is a 4.26-power law, and his exponential form applies ONLY above 36,000 ft. The docstring calls the code's model 'ISA', which is wrong: ISA is a lapse-rate barometric model, and the exponential isothermal form is a different atmosphere.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Called "ISA" but is not ISA — ISA is a lapse-rate barometric model, this is isothermal exponential. Name contradicts the definition, and the same function body is duplicated at powertrain_sizing_service.py:52.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "ISA air density approximation [kg/m³]."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
