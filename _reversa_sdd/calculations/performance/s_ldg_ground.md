---
name: s_ldg_ground
symbol: s_LDG_ground
kind: quantity
unit: m
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Landing ground roll

**Definition.** Distance from touchdown to full stop.

**Formula — as the code writes it.**

```
return k_ldg * wing_loading / (rho * cl_max_ldg)
```

**Inputs.** [[k_ldg_adjusted|Friction-adjusted landing coefficient]] · [[wing_loading_fl|Wing loading (field length)]] · [[rho_sl|Sea-level ISA density]] · [[cl_max_ldg_fl|Landing CL_max (field length)]]

**Produced by.** `app/services/field_length_service.py:264` — `_compute_s_ldg_ground`

**Consumed by.**

- in this graph: [[s_ldg_50ft|Landing distance from 50 ft]] · [[s_obstacle_factor_apply|Obstacle-corrected distance]]
- outside it: `compute_field_lengths:435` · `FieldLengthRead.s_ldg_ground_m:441`

**Source.** 🟡 PARTIAL

> Form SOURCED: Scholz 05_PreliminarySizing §5.1 / exam-matching-chart-design-point and Sadraey 2013 §4.3.2 - V_S = sqrt(2(W/S)/(rho*CL_max_L)), V_TD = k*V_S, s = V_TD^2/(2*mu*g), giving s proportional to (W/S)/(rho*CL_max_L). Constant 0.5847 NO_SOURCE (see k_ldg_hard).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
s_LDG_ground = k^2/(mu_brake*g) * (W/S)/(rho*CL_max,L)
```

**⚠️ Divergence from the source.** g is missing from the code's denominator, which is why K_LDG appears dimensionless when the sourced coefficient k^2/(mu*g) has units s^2/m. The model also omits aerodynamic drag and any flare/float distance, both of which the sources fold into a_braking.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Only cross-checked against a Cessna 172N at 1088 kg / 16.17 m^2 / CL_max_LDG 2.1. ADR 0023 requires validation at 0.5-15 kg and none is cited; the code comment presents the GA agreement (+/-15%) as if it validated the constant generally.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Only validated against a 1088 kg Cessna; ADR 0023 requires validation at RC/UAV scale (0.5–15 kg) and none is cited.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Calibration: Cessna 172N at MTOM (m=1088 kg, S=16.17 m², CL_max_LDG=2.1): W/S = 660 N/m²; s = 0.5847 × 660 / (1.225 × 2.1) ≈ 150 m (POH ≈ 160 m, within ±15%)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
