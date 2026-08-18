---
name: qprop-p-shaft
symbol: P_shaft
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Solved shaft power (QPROP)

**Definition.** Mechanical shaft power at the solved torque-balance point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_shaft = max(torque * omega, 0.0)
```

**Inputs.**

- [[qprop-torque|Solved shaft torque]]
- [[qprop-rpm-solution|Solved operating RPM]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_performance.py:581` — `solve_qprop_operating_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Shaft power per velocity sample`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:753`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.2: P_shaft = Q_m * Omega (identified as equation 6 in Drela's model).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P_shaft = Q_m * Omega
```

**⚠️ Anomaly.** On the QPROP branch this bypasses the p_shaft_max power ceiling entirely (line 753 clamps only at 0), while the non-QPROP branch clips to p_shaft_max (line 757). Two branches of the same field obey different limits.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Shaft power comes from the solved torque balance (Q·ω); already consistent with Cp·ρ·n³·D⁵ at the solution RPM.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
