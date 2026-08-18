---
name: alr-polar-cl0
symbol: cl0
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - flag/divergence
---

# CL at minimum drag (cl0)

**Definition.** CL at the vertex of the fitted parabolic drag polar.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl0_fit = -b_fit / (2.0 * k_fit)
```

**Inputs.**

- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:665` — `_extract_metrics`

**Consumed by.**

- in this graph: `CL at maximum L/D (closed form)` · `CD at target CL`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.cl0` · `best_ld_cl:760` · `score_target_cl:1023,1045`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 (parabola vertex); Abbott & von Doenhoff (1959), Ch. 6 — the low-drag range of a cambered section is centred on its design lift coefficient
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** cl0 = −b/(2k) is the exact vertex of the fitted quadratic. Its identification with the section's design C_l is supported by A&vD but not stated by either source in this algebraic form.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `cl0_fit = -b_fit / (2.0 * k_fit)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
