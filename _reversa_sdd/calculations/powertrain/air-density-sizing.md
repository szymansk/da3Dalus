---
name: air-density-sizing
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

# Air density at altitude (sizing)

**Definition.** Air density from the same isothermal exponential model as the performance module.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return RHO_SEA_LEVEL * math.exp(-altitude_m / 8500.0)
```

**Inputs.**

- [[air-density-sea-level-alias|Sea-level density alias (sizing)]]

**Produced by.** `app/services/powertrain_sizing_service.py:52` — `_air_density`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Power required for a motor+battery combo`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:91`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey (2013) Eq. 4.94a: sigma = (1 - 6.873e-6 h)^4.26, 0 <= h <= 36,000 ft.
```

**⚠️ Divergence from the source.** Same as air-density-perf: the exponential isothermal form with an 8500 m scale height matches neither Sadraey's troposphere power law (Eq. 4.94a) nor Anderson 6e §1.9. Calling it 'ISA' in the docstring is incorrect.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Byte-for-byte duplicate of powertrain_performance.py:348 — two independent producers of air density (ADR 0022). Called "ISA" but isothermal-exponential, and 8500 carries no citation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "ISA air density approximation."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
