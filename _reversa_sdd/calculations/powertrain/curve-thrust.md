---
name: curve-thrust
symbol: T(V)
kind: quantity
unit: N
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
---

# Thrust per velocity sample

**Definition.** Propeller thrust at each swept airspeed, from the interpolated thrust coefficient at the operating RPM.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
thrust_n = max(Ct * rho * (point_n_rps**2) * (D_m**4), 0.0)
```

**Inputs.**

- [[polar-ct|Propeller thrust coefficient]]  — *⊣ limit*
- [[air-density-perf|Air density at altitude (performance)]]
- [[curve-prop-rpm|Fixed operating RPM (non-QPROP branch)]]
- [[qprop-rpm-solution|Solved operating RPM]]  — *⊣ limit*
- [[curve-diameter-m|Propeller diameter in metres]]

**Produced by.** `app/services/powertrain_performance.py:748` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:766` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:255`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7: C_T = T/(rho n^2 D^4), rearranged for T.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
T = C_T rho n^2 D^4
```

**⚠️ Anomaly.** Duplicate of propop-thrust (line 406) — the same expression exists in two functions (ADR 0022). Reaches the API response but no UI consumer exists (notes F1).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring step 5c: "T = Ct·ρ·n²·D⁴ (clamped ≥ 0)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
