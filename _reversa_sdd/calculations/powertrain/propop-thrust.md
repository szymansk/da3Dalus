---
name: propop-thrust
symbol: T
kind: quantity
unit: N
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Propeller thrust (operating-point helper)

**Definition.** Thrust at a prescribed RPM and airspeed from the thrust coefficient.

**Formula — as the code writes it.**

```
thrust_n = Ct * rho * (n_rps**2) * (D_m**4) ; thrust_n = max(thrust_n, 0.0)
```

**Inputs.** [[polar-ct|Propeller thrust coefficient]] · [[air-density-perf|Air density at altitude (performance)]] · [[propop-n-rps|Propeller rotational speed (operating point)]]

**Produced by.** `app/services/powertrain_performance.py:406` — `compute_prop_operating_point`

**Consumed by.**

- outside it: `app/tests/test_powertrain_performance_service.py:252` · `app/tests/test_powertrain_performance_service.py:259` · `app/tests/test_powertrain_performance_service.py:268`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7, rearranged: T = C_T * rho * n^2 * D^4.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
C_T = T/(rho n^2 D^4)  =>  T = C_T rho n^2 D^4
```

**⚠️ Anomaly.** NO PRODUCTION CONSUMER — compute_prop_operating_point is called only from tests. compute_performance_curve does not call it; it re-implements the identical thrust expression inline at line 748. Two independent producers of the same user-visible number (ADR 0022) and a dead public function (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Thrust from Ct: T = Ct · ρ · n² · D⁴`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
