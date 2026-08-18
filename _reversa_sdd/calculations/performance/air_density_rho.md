---
name: air_density_rho
symbol: ρ
kind: quantity
unit: kg/m³
cluster: perf-oppoints
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/sourced
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Air density at the operating altitude

**Definition.** ISA density used for the dynamic pressure in CL_target.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rho = float(asb.Atmosphere(altitude=altitude).density())
```

**Inputs.**

- [[default_altitude_m|Default environment altitude]]  — *ε tolerance*

**Produced by.** `app/services/operating_point_generator_service.py:884` — `_trim_or_estimate_point`

**Consumed by.**

- in this graph: `Target lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:894 (cl_target_fn)`

**Source.** 🟢 SOURCED

> AeroSandbox 4.2 `asb.Atmosphere` — 'fully differentiable interface to the International Standard Atmosphere (ISA), specifically the U.S. 1976 COESA standard'. Sea-level ρ₀ = 1.225 kg/m³ as used by Sadraey §4.3.2/§4.3.5.2.
>
> — via `aerosandbox-expert, aircraft-design-scholz`

**The source states it as.**

```
rho = ISA/U.S. Standard Atmosphere 1976 at geometric altitude
```

**⚠️ Divergence from the source.** Delegating to a standard atmosphere model is correct and matches the sizing convention (sea level as reference). No divergence.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
