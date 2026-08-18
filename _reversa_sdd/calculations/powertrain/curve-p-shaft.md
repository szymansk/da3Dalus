---
name: curve-p-shaft
symbol: P_shaft(V)
kind: quantity
unit: W
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

# Shaft power per velocity sample

**Definition.** Shaft power at each swept airspeed. On the QPROP branch it is the solved torque-balance power; otherwise it is the Cp-derived power clipped to the shaft-power ceiling.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_shaft_w = float(max(op.p_shaft_w, 0.0))   # QPROP branch
p_shaft_uncapped = Cp * rho * (point_n_rps**3) * (D_m**5) ; p_shaft_w = float(np.clip(p_shaft_uncapped, 0.0, p_shaft_max))   # fixed-RPM branch
```

**Inputs.**

- [[polar-cp|Propeller power coefficient]]  — *⊣ limit*
- [[air-density-perf|Air density at altitude (performance)]]
- [[curve-prop-rpm|Fixed operating RPM (non-QPROP branch)]]
- [[curve-diameter-m|Propeller diameter in metres]]
- [[curve-p-shaft-max|Shaft power ceiling]]  — *⊣ limit*
- [[qprop-p-shaft|Solved shaft power (QPROP)]]

**Produced by.** `app/services/powertrain_performance.py:757` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:767` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:255`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7: C_P = P/(rho n^3 D^5), rearranged for P (fixed-RPM branch); Drela, 'DC Motor / Propeller Matching' §1.2, P_shaft = Q Omega (QPROP branch).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P = C_P rho n^3 D^5  (Brandt & Selig);  P_shaft = Q Omega  (Drela §1.2)
```

**⚠️ Divergence from the source.** No source prescribes clipping shaft power at an externally computed ceiling. In Drela's model the power ceiling is enforced implicitly by the torque balance and the current limit, not by a post-hoc clip; the code applies the clip on one branch and not the other.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Clipping at p_shaft_max is a silent truncation with no DesignWarning (ADR 0020) — a sample that is power-limited is indistinguishable from one that is not. Also duplicates propop-p-shaft (line 411).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring step 5d: "P_shaft = min(Cp·ρ·n³·D⁵, P_shaft_max)  — power ceiling"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
