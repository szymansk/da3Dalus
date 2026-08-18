---
name: alr-level-flight-cl
symbol: CL
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Level-flight lift coefficient

**Definition.** CL required for level flight at a given mass, speed and wing area.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = 0.5 * RHO * v_ms**2
return (mass_kg * G) / (q * s_ref_m2)
```

**Inputs.**

- [[alr-g|Standard gravity]]
- [[alr-rho|ISA sea-level density (low-Re module)]]

**Produced by.** `app/services/airfoil_low_re_service.py:707` — `_level_flight_cl`

**Consumed by.**

- in this graph: `target_cl_best_glide` · `target_cl_cruise` · `target_cl_min_sink`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `suitability_service.py:336,346,356 → target_cl_cruise / best_glide / min_sink`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (L = q∞ S C_L, q∞ = ½ρV²) with the steady-level-flight condition L = W
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = W/(q∞ S) = mg/(½ρV²S)
```

**⚠️ Divergence from the source.** Identical. Assumes ρ = ISA SL and zero climb angle; both are implicit in the code, neither is exposed to the user.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Private-by-name (`_level_flight_cl`) yet imported across a service boundary (suitability_service.py:61).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `q = 0.5 * RHO * v_ms**2
return (mass_kg * G) / (q * s_ref_m2)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
