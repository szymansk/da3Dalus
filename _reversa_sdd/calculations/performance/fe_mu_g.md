---
name: fe_mu_g
symbol: mu_g
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# Gust mass ratio

**Definition.** Dimensionless mass parameter governing gust alleviation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return 2.0 * wing_loading / (rho * c_mgc * cl_alpha * g)
```

**Inputs.**

- [[fe_wing_loading|Wing loading (gust path)]]
- [[fe_rho_default|Default air density (flight envelope)]]  — *⤵ fallback*
- [[fe_c_mgc|Mean geometric chord]]
- [[fe_effective_cl_alpha|Effective lift-curve slope for gust]]  — *⤵ fallback*
- [[fe_gravity|Gravitational acceleration (flight envelope)]]

**Produced by.** `app/services/flight_envelope_service.py:89` — `_compute_mu_g`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Pratt validity warning` · `Gust alleviation factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> FAR 25.341(c) / CS-25.341(c), gust mass-ratio definition; origin Pratt & Walker, NACA TN 2964 (1953), republished as NACA Report 1206 (1954).
>
> — via `scholz`

**The source states it as.**

```
mu_g = 2*(W/S) / (rho * c_bar * a * g)
```

**⚠️ Scale (ADR 0023).** Formula transcription is exact. FAR-25 evaluates it at flight-altitude rho and the weight under consideration; the code fixes rho at sea level. At RC W/S (30-120 N/m^2) mu_g typically lands at 1-4, i.e. at or below the band the warning itself flags.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `"Sources: FAR-25.341(a)(2); NACA TN 2964 (Pratt & Walker, 1953)."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
