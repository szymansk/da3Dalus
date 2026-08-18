---
name: ss-motor-cont-shaft
symbol: motor_cont_w
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Required motor continuous shaft power

**Definition.** Mechanical shaft power the motor must sustain at cruise.

**Formula — as the code writes it.**

```
motor_cont_shaft_w = p_aero_cruise / eta_mid
```

**Inputs.** [[ss-p-aero-cruise|Aerodynamic power at cruise]] · [[ss-eta-mid|Mid-band propeller efficiency]]

**Produced by.** `app/services/powertrain_solution_space_service.py:422` — `compute_solution_space`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:454` · `app/services/powertrain_solution_space_service.py:483`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15 / §8.7 Eq. 8.2, evaluated at cruise speed: P_shaft = P_aero(V_C)/eta_P. Roxxy Motoren-Fibel, Ch. 3, pp. 28-29 establishes why the continuous figure matters: above 150 degC the copper enamel melts, so sustained power is thermally bounded.
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
P_shaft,cont = P_aero(V_C) / eta_P
```

**⚠️ Divergence from the source.** The Roxxy source makes this the thermally decisive rating ('careful attention to continuous vs. burst power ratings are critical in aircraft design'), yet it is the one quantity in the response that no UI surface renders.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO UI CONSUMER — present on both SolutionRow and ShoppingSpec, typed in usePowertrainSolutionSpace.ts:34 and :56, rendered nowhere (notes F6). The continuous rating is the one that actually determines motor thermal survival, and it is the one the user is never shown.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `schema: "Motor continuous shaft power required [W] (= P_aero(V_cruise) / η_prop_mid)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
