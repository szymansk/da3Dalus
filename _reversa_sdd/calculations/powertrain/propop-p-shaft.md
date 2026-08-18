---
name: propop-p-shaft
symbol: P_shaft
kind: quantity
unit: W
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

# Propeller shaft power (operating-point helper)

**Definition.** Shaft power absorbed by the propeller at a prescribed RPM, taken from the power coefficient rather than from the stored torque column.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_shaft_w = Cp * rho * (n_rps**3) * (D_m**5) ; p_shaft_w = max(p_shaft_w, 0.0)
```

**Inputs.**

- [[polar-cp|Propeller power coefficient]]  — *⊣ limit*
- [[air-density-perf|Air density at altitude (performance)]]
- [[propop-n-rps|Propeller rotational speed (operating point)]]

**Produced by.** `app/services/powertrain_performance.py:411` — `compute_prop_operating_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/tests/test_powertrain_performance_service.py:252` · `app/tests/test_powertrain_performance_service.py:293`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7, rearranged: P = C_P * rho * n^3 * D^5, where P is the mechanical shaft power supplied to the propeller.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
C_P = P/(rho n^3 D^5)  =>  P = C_P rho n^3 D^5
```

**⚠️ Divergence from the source.** The function docstring claims torque is derived from PWR_W/(2*pi*n); the source relation the code actually implements is the C_P one. The docstring describes a different derivation than the code performs.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO PRODUCTION CONSUMER (same dead function as propop-thrust). Also the docstring claims torque is derived from PWR_W/(2*pi*n), but the body never reads PWR_W — it uses Cp. Docstring contradicts the code.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Shaft power from Cp: P = Cp · ρ · n³ · D⁵ / This is the correct path — NOT from stored Torque_Nm (UAT note). Function docstring: "Torque is derived from PWR_W / (2π·n), NOT from stored Torque_Nm, which loses precision at 3 decimal places for low-RPM rows (UAT note, comment #4)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
