---
name: lfop-alpha-trimmed
symbol: alpha_trimmed
kind: quantity
unit: deg
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Trimmed alpha from CL-target solve

**Definition.** Alpha at which AeroBuildup CL equals the level-flight target, found by Brent root-finding.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_trimmed = brentq(_cl_at_alpha, -5.0, 15.0, xtol=0.05, maxiter=30)
```

**Inputs.**

- [[lfop-cl-target-clip|Target CL clamp]]  — *⊣ limit*

**Produced by.** `app/services/section_aoa_service.py:526` — `_resolve_level_flight_op`

**Consumed by.**

- outside it: `OperatingPointSchema.alpha`

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.6.2 (the cruise condition is defined by C_L required from L = W; alpha follows from the aircraft's CL(alpha))
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Solve CL_aircraft(alpha) = CL_required for alpha
```

**⚠️ Divergence from the source.** Method is the standard trim-for-level-flight solve. Note this is a LIFT trim only, not a moment trim — Cm = 0 is never enforced, so 'trimmed' in the variable name is stronger than what is computed.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:526`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
