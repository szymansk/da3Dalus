---
name: motor-io-input
symbol: I0
kind: parameter
unit: A
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# No-load current

**Definition.** Motor no-load current, the torque-producing current offset in the QPROP model. Defaults to 0 A when absent.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.0 (fallback via `motor.io_no_load_a or 0.0`)`

**Formula — as the code writes it.**

```
i0 = motor.io_no_load_a or 0.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:523` — `solve_qprop_operating_point`

**Consumed by.**

- in this graph: `QPROP motor efficiency` · `Motor-produced torque` · `Solved shaft torque`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:535` · `app/services/powertrain_performance.py:580` · `app/services/powertrain_performance.py:585`

**Source.** 🟢 SOURCED

> Drela, M., 'DC Motor / Propeller Matching' theory notes, §1.1: i_0 is the zero-torque current capturing 'nonlinear friction and windage losses appearing as a constant current draw that produces no torque. Typically 0.5-2 A for small RC motors.' Measured from free-spin tests.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Q_m = (I - i_0)/K_Q ;  i_0 typically 0.5-2 A for small RC motors
```

**⚠️ Divergence from the source.** The code defaults i_0 to 0 A when absent. The source gives 0.5-2 A as the typical range for exactly this motor class, so the default is outside the cited range, not merely at its edge. It makes the motor loss-free at no load and inflates the reported efficiency.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: substituting I0 = 0 makes the motor loss-free at no load and raises the reported efficiency, with no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Io defaults to 0 A if not provided (an ideal-loss-free no-load assumption), so Rm alone is sufficient to unlock the torque-balance solver."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
