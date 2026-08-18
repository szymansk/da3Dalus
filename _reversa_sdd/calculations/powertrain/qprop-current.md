---
name: qprop-current
symbol: I
kind: quantity
unit: A
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Solved terminal current

**Definition.** Motor terminal current at the solved operating point, floored at zero.

**Formula — as the code writes it.**

```
current = max(current_for_rpm(rpm_sol), 0.0)
```

**Inputs.** [[qprop-rpm-solution|Solved operating RPM]] · [[qprop-current-for-rpm|Terminal current at a candidate RPM]]

**Produced by.** `app/services/powertrain_performance.py:578` — `solve_qprop_operating_point`

**Consumed by.**

- in this graph: [[qprop-eta-motor|QPROP motor efficiency]] · [[qprop-torque|Solved shaft torque]]
- outside it: `app/services/powertrain_performance.py:580` · `app/services/powertrain_performance.py:585` · `app/services/powertrain_performance.py:590`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1: i = (V - Omega/K_v)/R, evaluated at the solved operating speed.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
i = (V - Omega/K_v) / R
```

**⚠️ Anomaly.** Returned on QpropOperatingPoint.current_a but never surfaced in PerformanceSample — the solved current, the single most useful number for ESC/battery selection, is discarded by compute_performance_curve.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
