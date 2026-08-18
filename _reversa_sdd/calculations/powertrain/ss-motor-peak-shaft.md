---
name: ss-motor-peak-shaft
symbol: motor_peak_w
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Required motor peak shaft power

**Definition.** Mechanical shaft power the motor must deliver at top speed — aerodynamic power divided by mid-band propeller efficiency only (motor and ESC efficiencies excluded because the rating is a shaft rating).

**Formula — as the code writes it.**

```
motor_peak_shaft_w = p_aero_top / eta_mid
```

**Inputs.** [[ss-p-aero-top|Aerodynamic power at top speed]] · [[ss-eta-mid|Mid-band propeller efficiency]]

**Produced by.** `app/services/powertrain_solution_space_service.py:421` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-catalog-motor-match|Catalog motor match flag]]
- outside it: `app/services/powertrain_solution_space_service.py:425` · `app/services/powertrain_solution_space_service.py:453` · `app/services/powertrain_solution_space_service.py:482`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §8.8.1, Eq. 8.15: eta_P = T V/P_in, and §8.7 Eq. 8.2: T = P eta_P / V_C, rearranged to P = T V/eta_P. Sadraey's §8.8.1 sizing recipe is exactly this: 'Required engine power at altitude: P_alt = T V_C / eta_P.'
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_shaft = T V / eta_P  (Sadraey Eq. 8.15 / Eq. 8.2);  sizing form P_alt = T V_C / eta_P (§8.8.1)
```

**⚠️ Divergence from the source.** The formula matches Sadraey's sizing recipe exactly — dividing aerodynamic power by the propeller efficiency ONLY (not by motor or ESC efficiency) is correct for a shaft-power requirement, and the code's docstring says so. The divergence is downstream: the frontend independently recomputes ceil(p_aero_top_w / eta_prop_lo), so the number the user sees uses a different efficiency (eta_prop_lo, not eta_mid) than the backend's cited implementation of Eq. 8.15.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's worked application of this equation (Example 8.3, §8.8.1) uses eta_P = 0.75 for a transport turboprop; at RC scale the correct efficiency band is the 0.60-0.70 plateau of Deters/Ananda/Selig (2014) §VI. The formula transfers; Sadraey's efficiency value does not.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** SECOND PRODUCER (ADR 0022). The number the user actually sees in the Motor (W) column and the shopping line is the frontend's independent conservativeMotorW = ceil(p_aero_top_w / eta_prop_lo) (frontend/components/workbench/PowertrainTab.tsx:110, rendered at :571 and :464). This backend field and its twin ShoppingSpec.motor_min_peak_w are computed, shipped, typed in the hook — and never read. The two differ by eta_prop_lo vs eta_mid (~10 %). Also cell-count-independent, yet emitted once per row.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Required motor SHAFT power (P_aero / η_prop), not aerodynamic power.  Schema: "Motor peak shaft power required [W] (= P_aero(V_top) / η_prop_mid)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
