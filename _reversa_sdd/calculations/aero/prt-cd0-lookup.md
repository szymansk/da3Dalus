---
name: prt-cd0-lookup
symbol: C_D0(V)
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# cd0 at query velocity

**Definition.** cd0 interpolated between table rows linearly in 1/√Re per Blasius scaling.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
t = (inv_sqrt_query - inv_sqrt_lo) / denom
return float(cd0_lo + t * (cd0_hi - cd0_lo))
```

**Inputs.**

- [[prt-cd0-fit|Band cd0 (fitted intercept)]]
- [[prt-re-aircraft|Aircraft-level Reynolds number (V-band label)]]

**Produced by.** `app/services/polar_re_table_service.py:176` — `lookup_cd0_at_v`

**Consumed by.**

- outside it: `app/services/speed_polar_service.py:142` · `app/services/matching_chart_service.py:822` · `app/services/assumption_compute_service.py:580,2067` · `app/services/endurance_service.py:347,353`

**Source.** 🟡 PARTIAL

> Anderson 6e §4.12.1 (laminar flat plate C_f = 1.328/√Re_c) and §4.12.2 (turbulent C_f = 0.074/Re_c^0.2)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_f,lam ∝ Re^(-1/2); C_f,turb ∝ Re^(-1/5)
```

**⚠️ Divergence from the source.** The Re^(-1/2) law is sourced only for a fully laminar flat plate. This cd0 is a whole-aircraft parasite drag containing turbulent skin friction (Re^(-1/5)) plus form and interference drag that follow no flat-plate law. Interpolating linearly in 1/√Re between two fitted rows is a defensible engineering choice, not a derived result — the code's own docstring calls it 'pragmatic'.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `inv_sqrt_lo = 1.0 / math.sqrt(re_lo)
inv_sqrt_query = 1.0 / math.sqrt(re_query)
t = (inv_sqrt_query - inv_sqrt_lo) / denom
return float(cd0_lo + t * (cd0_hi - cd0_lo))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
