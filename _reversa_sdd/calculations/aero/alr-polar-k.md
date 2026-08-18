---
name: alr-polar-k
symbol: k
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/divergence
---

# Airfoil polar curvature k

**Definition.** Quadratic coefficient of the 2D drag polar around cl0.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
k_fit = float(p[0])
```

**Inputs.**

- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:661` — `_extract_metrics`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `CL at maximum L/D (closed form)` · `CD at target CL`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.k` · `best_ld_cl:760` · `score_target_cl:1022,1045`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 — k is the C_L² coefficient of the parabolic polar
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** For a 2D section k has no π·e·AR interpretation (that is the finite-wing induced-drag term); here it is purely the curvature of the fitted section polar. Same form, different meaning — worth keeping distinct from prt-k-fit.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `k_fit = float(p[0])`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
