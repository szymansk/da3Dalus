---
name: bwsd-re-local
symbol: re_local
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
---

# Local section Reynolds number

**Definition.** Chord Reynolds number of a section at the operating velocity, floored at 1e4.

**Formula — as the code writes it.**

```
re_local=max(velocity * entry.chord_m / nu, 1e4),
```

**Inputs.** [[bwsd-nu|Kinematic viscosity (section builder)]] · [[saoa-chord|Panel chord]]

**Produced by.** `app/services/turbulator_optimizer_service.py:442` — `build_wing_section_data`

**Consumed by.**

- in this graph: [[tos-cd-at-cl|Section cd at a target CL and trip position]] · [[tos-re-rep|Representative Reynolds number (whole scope)]]
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorSectionResult.re_local` · `frontend/components/workbench/TurbulatorEditDialog.tsx`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.7 and §4.12 (Re_c = rho*V*c/mu = V*c/nu)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
Re_c = V * c / nu
```

**⚠️ Divergence from the source.** Form exact. Inherits the nu = 1.5e-5 rounding and the sea-level-only assumption from bwsd-nu, and the 1e4 floor is applied here too without a warning.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:442`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
