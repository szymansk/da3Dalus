---
name: motor-uses-qprop-model
symbol: uses_qprop_model
kind: quantity
unit: boolean
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
  - flag/divergence
---

# QPROP model availability flag

**Definition.** True when winding resistance Rm is present, which switches the performance curve from the fixed-RPM approximation to the QPROP torque-balance solver. Io is allowed to default to 0 A.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return self.rm_ohm is not None and self.rm_ohm > 0
```

**Inputs.**

- [[motor-rm-ohm-input|Winding resistance]]

**Produced by.** `app/services/powertrain_performance.py:122` — `MotorSpec.uses_qprop_model`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Estimated-power flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:701` · `app/tests/test_powertrain_qprop_motor.py:120`

**Source.** 🟢 SOURCED

> Drela, M., 'DC Motor / Propeller Matching' theory notes, §1.1 — the three-parameter DC motor model requires exactly R (winding resistance), Kv (speed constant) and i0 (zero-torque current); 'i0 typically 0.5-2 A for small RC motors'.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V = i*R + Omega/Kv ;  Q_m = (I - i0)/K_Q  — three parameters R, Kv, i0
```

**⚠️ Divergence from the source.** Drela's model needs all THREE parameters. The code unlocks the solver on Rm alone and lets i0 default to 0 A, which the source contradicts by stating i0 is typically 0.5-2 A for small RC motors. Setting i0 = 0 removes the friction/windage loss term entirely.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The fidelity switch is exposed to the user only as free text inside the notes string (lines 781-796), not as a structured field. Two physically different models can return the same response shape with no machine-readable marker.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Requires winding resistance Rm. Io defaults to 0 A if not provided (an ideal-loss-free no-load assumption), so Rm alone is sufficient to unlock the torque-balance solver."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
