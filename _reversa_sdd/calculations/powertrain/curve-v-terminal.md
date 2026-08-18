---
name: curve-v-terminal
symbol: V_terminal
kind: quantity
unit: V
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Motor terminal voltage

**Definition.** Voltage presented at the motor terminals for the QPROP solve: pack voltage scaled linearly by throttle.

**Formula — as the code writes it.**

```
v_terminal = V_bat * request.throttle
```

**Inputs.** [[curve-v-bat|Battery voltage used for the curve]] · [[request-throttle|Throttle fraction]]

**Produced by.** `app/services/powertrain_performance.py:702` — `compute_performance_curve`

**Consumed by.**

- in this graph: [[qprop-back-emf-floor|Back-EMF floor at the current ceiling]] · [[qprop-current-for-rpm|Terminal current at a candidate RPM]] · [[qprop-eta-motor|QPROP motor efficiency]] · [[qprop-rpm-free|Free-running RPM]]
- outside it: `app/services/powertrain_performance.py:718`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, ESC control chapter (PWM switching and coil currents): 'A duty cycle of 50% applies an average voltage of approximately half the battery voltage; at 100% duty cycle, full voltage is applied ... This linear relationship between throttle command (duty cycle) and effective voltage is why PWM allows smooth, proportional motor control.' Worked example: 25% duty -> ~3 V on a 12 V pack, 50% -> ~6 V, 100% -> 12 V.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_eff = duty_cycle x V_battery
```

**⚠️ Divergence from the source.** None in form — the source states the linear duty-cycle-to-effective-voltage relation the code implements. Note the contrasting statement in RC-Network Wiki 'Motorsteller': throttle stick position maps to RPM percentage, and because propeller power scales with RPM cubed, half throttle yields roughly 12.5% of maximum POWER. That is consistent with (not contrary to) the linear voltage model, but it means throttle is not linear in power.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Models an ESC as a linear voltage divider (throttle x V_bat). A PWM ESC delivers duty-cycle-averaged voltage with different loss behaviour; no source is cited for the linear model.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# V_terminal = battery × throttle.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
