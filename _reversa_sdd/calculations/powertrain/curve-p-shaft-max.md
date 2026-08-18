---
name: curve-p-shaft-max
symbol: P_shaft_max
kind: quantity
unit: W
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Shaft power ceiling

**Definition.** Maximum shaft power available, the electrical ceiling times motor efficiency.

**Formula — as the code writes it.**

```
p_shaft_max = p_available_elec * motor.eta_motor
```

**Inputs.** [[curve-p-available-elec|Electrical power ceiling]] · [[motor-eta|Motor + gearbox efficiency]]

**Produced by.** `app/services/powertrain_performance.py:663` — `compute_performance_curve`

**Consumed by.**

- in this graph: [[curve-p-shaft|Shaft power per velocity sample]] · [[infeasibility-threshold-w|Infeasible-powertrain warning threshold]]
- outside it: `app/services/powertrain_performance.py:687` · `app/services/powertrain_performance.py:757`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.2: eta_m = P_shaft/(V*I), i.e. P_shaft = eta_m * P_electrical.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P_shaft = eta_m * P_el
```

**⚠️ Anomaly.** Ignored entirely on the QPROP branch (line 753) — the ceiling only constrains the simplified model.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring step 4: "P_shaft_max = P_available_elec × η_motor"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
