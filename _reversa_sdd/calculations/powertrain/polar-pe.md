---
name: polar-pe
symbol: Pe
kind: quantity
unit: dimensionless (0..1)
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

# Propeller efficiency from polar

**Definition.** Propulsive efficiency of the propeller at the interpolated operating point, recomputed from the clamped Ct and Cp rather than read from the stored Pe column. Zero at J=0.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if Cp_interp > 0 and J_clamp > 0: Pe_interp = Ct_interp * J_clamp / Cp_interp ; else: Pe_interp = 0.0
```

**Inputs.**

- [[polar-ct|Propeller thrust coefficient]]  — *⊣ limit*
- [[polar-cp|Propeller power coefficient]]  — *⊣ limit*
- [[polar-j-clamp|Clamped advance ratio for interpolation]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_performance.py:336` — `interpolate_ct_cp_pe`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Propeller efficiency per velocity sample` · `Propeller efficiency (operating-point helper)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:415` · `app/services/powertrain_performance.py:760`

**Source.** 🟢 SOURCED

> Deters, R.W., Ananda, G.K. & Selig, M.S. (2014), small-scale propeller performance characterization, §II.D, Eq. 7: eta = J * C_T / C_P, derived from eta = TV/P. Same relation in Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta = J * C_T / C_P  (equivalently eta = T V / P)
```

**⚠️ Divergence from the source.** None in form. The source confirms eta_static = 0 at J = 0, matching the code's zero branch.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** PropellerPolarRow carries a stored Pe column (line 71) that is loaded from the DB (endpoint line 157) and then never read — the value is always recomputed. A second, unused producer of the same number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Pe = Ct·J/Cp (undefined/0 at J=0)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
