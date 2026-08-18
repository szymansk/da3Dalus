---
name: motor-rm-ohm-input
symbol: Rm
kind: parameter
unit: ohm
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Winding resistance

**Definition.** Terminal-to-terminal motor winding resistance. Its presence alone switches the whole performance model.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:104` — `MotorSpec.rm_ohm`

**Consumed by.**

- in this graph: [[motor-uses-qprop-model|QPROP model availability flag]] · [[qprop-back-emf-floor|Back-EMF floor at the current ceiling]] · [[qprop-current-for-rpm|Terminal current at a candidate RPM]] · [[qprop-eta-motor|QPROP motor efficiency]]
- outside it: `app/services/powertrain_performance.py:122` · `app/services/powertrain_performance.py:518` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:102`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1: R is the motor winding resistance in ohms, 'constant across the operating envelope; includes brush and contact resistance', measurable by ohmmeter or locked-rotor V-I. One of the three parameters (R, Kv, i0) of the model.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V = i R + Omega/K_v
```

**Cited in the code itself.** `field description: "Motor winding (terminal-to-terminal) resistance Rm [Ω]. When provided, enables the QPROP 3-parameter torque-balance model (gh-1006); when absent the simplified fixed-RPM model is used."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
