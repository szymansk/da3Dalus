---
name: alr-polar-cd0
symbol: cd0
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
  - flag/anomaly
  - flag/divergence
---

# Airfoil cd0 (parabolic fit vertex)

**Definition.** Minimum drag coefficient of the fitted 2D parabolic polar CD = cd0 + k(CL−cl0)².

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p = np.polyfit(cl_f, cd_f, 2)
k_fit = float(p[0]); b_fit = float(p[1]); c_fit = float(p[2])
cl0_fit = -b_fit / (2.0 * k_fit)
cd0_fit = c_fit - k_fit * cl0_fit**2
```

**Inputs.**

- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*
- [[alr-confidence-gate|NeuralFoil confidence gate]]

**Produced by.** `app/services/airfoil_low_re_service.py:666` — `_extract_metrics`

**Consumed by.**

- in this graph: `CL at maximum L/D (closed form)` · `CD at target CL` · `Relative drag-rise ratio r` · `Efficiency component of score_target_cl` · `Per-Re fleet cd0 reference`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.cd0` · `score_target_cl:1021` · `compute_re_cd0_reference:815` · `best_ld_cl:758`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 — parabolic drag polar C_D = C_D0 + kC_L²
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_D = C_D0 + k C_L²
```

**⚠️ Divergence from the source.** The code fits the offset form C_D = cd0 + k(C_L − cl0)². Anderson's polar is symmetric about C_L = 0; the cl0-offset generalisation for cambered sections is common engineering practice but no source consulted states it in that form. Name also collides with the aircraft-level cd0 in polar_re_table_service — same slug, 2D section vs whole-aircraft parasite.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Name collides with the aircraft-level cd0 from polar_re_table_service — the same slug means a 2D section value here and a whole-aircraft parasite drag there.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `p = np.polyfit(cl_f, cd_f, 2)
k_fit = float(p[0])
b_fit = float(p[1])
c_fit = float(p[2])
if k_fit > 0:
    cl0_fit = -b_fit / (2.0 * k_fit)
    cd0_fit = c_fit - k_fit * cl0_fit**2`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
