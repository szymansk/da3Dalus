---
name: qprop-eta-motor
symbol: eta_motor (QPROP)
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# QPROP motor efficiency

**Definition.** Electrical-to-mechanical efficiency at the solved operating point in Drela's QPROP form, clamped to [0,1].

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
eta = (V_terminal - current * rm) * (current - i0) / (V_terminal * current) ; eta = float(min(max(eta, 0.0), 1.0))
```

**Inputs.**

- [[qprop-current|Solved terminal current]]  — *⊣ limit*
- [[curve-v-terminal|Motor terminal voltage]]
- [[motor-rm-ohm-input|Winding resistance]]
- [[motor-io-input|No-load current]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_performance.py:585` — `solve_qprop_operating_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:590`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.2: eta_m = P_shaft/(V*I), with the closed form eta_m = [1/(1 + i R K_V/Omega)] * (K_V/K_Q); loss partition P_in = I^2 R (resistive) + i_o V (friction) + P_shaft.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_m = P_shaft/(V I) = [1/(1 + i R K_V/Omega)] * (K_V/K_Q)
```

**⚠️ Divergence from the source.** The code writes eta = (V - I*Rm)(I - I0)/(V*I). This is algebraically the same quantity as Drela's expression when K_Q = K_V (numerator = Omega/Kv * (I-I0)/Kv * ... expanded through P_shaft = Q*Omega), but it is stated in a different form than either of Drela's two given expressions, and it implicitly assumes K_Q = K_V, which §1.1 flags as an approximation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Computed and stored on QpropOperatingPoint.eta_motor but never read by any caller — compute_performance_curve uses op.rpm and op.p_shaft_w only. Second, unused producer of motor efficiency alongside MotorSpec.eta_motor (line 147).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Motor efficiency at the solution is the QPROP form η = (V_terminal − I·Rm)·(I − I0) / (V_terminal·I)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
