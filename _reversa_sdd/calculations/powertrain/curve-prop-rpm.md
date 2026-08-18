---
name: curve-prop-rpm
symbol: prop_rpm
kind: quantity
unit: rpm
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Fixed operating RPM (non-QPROP branch)

**Definition.** Propeller RPM in the simplified model: gear-aware KV times pack voltage times throttle, independent of aerodynamic load.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
prop_rpm = motor.output_kv * V_bat * request.throttle
```

**Inputs.**

- [[motor-output-kv|Output-shaft KV]]
- [[curve-v-bat|Battery voltage used for the curve]]  — *⊣ limit*
- [[request-throttle|Throttle fraction]]

**Produced by.** `app/services/powertrain_performance.py:643` — `compute_performance_curve`

**Consumed by.**

- in this graph: `Advance ratio per velocity sample` · `Shaft power per velocity sample` · `Thrust per velocity sample` · `Nearest-RPM polar row group`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:666` · `app/services/powertrain_performance.py:696` · `app/services/powertrain_performance.py:728`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'No-load RPM = KV x Battery Voltage (volts)'; combined with Roxxy Motoren-Fibel ESC/PWM section, where duty cycle scales the effective terminal voltage linearly ('A duty cycle of 50% applies an average voltage of approximately half the battery voltage').
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
RPM_no-load = KV x V_battery
```

**⚠️ Divergence from the source.** The source calls this the NO-LOAD RPM. The code uses it as the actual operating RPM under aerodynamic load. Drela ('DC Motor / Propeller Matching' §1.1) shows the loaded speed is always lower, because Omega = Kv(V - iR) and the propeller torque demand forces i > 0. The simplification is documented in the code but is a departure from both sources.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the operating RPM alongside qprop-rpm-solution; which one runs depends on whether rm_ohm happens to be populated in the catalog row, and the response carries no structured field saying which.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Simplification note (gh-615): No Rm (winding resistance) — can't solve the full QPROP voltage/current operating point. RPM is fixed at output_kv × V_battery rather than solving for the torque-balance equilibrium."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
