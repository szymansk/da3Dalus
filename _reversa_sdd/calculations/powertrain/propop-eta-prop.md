---
name: propop-eta-prop
symbol: eta_prop
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - flag/anomaly
---

# Propeller efficiency (operating-point helper)

**Definition.** Propulsive efficiency at the operating point, passed straight through from the interpolated Pe.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
eta_prop = Pe ; eta_prop = max(eta_prop, 0.0)
```

**Inputs.**

- [[polar-pe|Propeller efficiency from polar]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_performance.py:415` — `compute_prop_operating_point`

**Consumed by.**

- outside it: `app/tests/test_powertrain_performance_service.py:300` · `app/tests/test_powertrain_performance_service.py:311`

**Source.** 🟢 SOURCED

> Deters, Ananda & Selig (2014), §II.D, Eq. 7: eta = J C_T / C_P.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta = J * C_T / C_P
```

**⚠️ Anomaly.** NO PRODUCTION CONSUMER (dead function).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# η_prop = Pe = Ct·J/Cp (already computed in interpolate_ct_cp_pe)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
