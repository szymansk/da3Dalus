---
name: motor-kv-si
symbol: Kv_si
kind: quantity
unit: rad/(s.V)
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Motor speed constant in SI

**Definition.** Output-shaft rad/s per volt of back-EMF. Its reciprocal is the torque constant Kt = 1/Kv_si [Nm/A], the basis of the QPROP torque relation.

**Formula — as the code writes it.**

```
return self.output_kv * 2.0 * math.pi / 60.0
```

**Inputs.** [[motor-output-kv|Output-shaft KV]]

**Produced by.** `app/services/powertrain_performance.py:131` — `MotorSpec.kv_si`

**Consumed by.**

- in this graph: [[qprop-back-emf|Motor back-EMF]] · [[qprop-motor-torque|Motor-produced torque]] · [[qprop-rpm-at-imax|RPM at the current ceiling]] · [[qprop-rpm-free|Free-running RPM]] · [[qprop-torque|Solved shaft torque]]
- outside it: `app/services/powertrain_performance.py:522` · `app/services/powertrain_performance.py:529` · `app/services/powertrain_performance.py:535` · `app/services/powertrain_performance.py:540` · `app/services/powertrain_performance.py:549` · `app/services/powertrain_performance.py:580`

**Source.** 🟢 SOURCED

> Drela, M., 'DC Motor / Propeller Matching' theory notes (QPROP documentation), §1.1.3 and §2.3: 'Kv is commonly specified in RPM/Volt, but the theoretical equations require rad/s/Volt. The conversion is Kv[rad/s/V] = Kv[RPM/V] x 2pi / 60.' Same source: in the ideal zero-friction, zero-resistance case the torque constant Kt equals Kv.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Kv[rad/s/V] = Kv[RPM/V] x 2*pi / 60 ;  Kt = 1/Kv_si [Nm/A]
```

**Cited in the code itself.** `docstring: "Kv_si = output_kv [rpm/V] × 2π/60. In SI the torque constant Kt = 1/Kv_si [Nm/A], which is the basis of the QPROP torque relation Q = (I − I0)/Kv_si."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
