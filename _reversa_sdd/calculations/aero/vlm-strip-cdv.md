---
name: vlm-strip-cdv
symbol: cdv
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: numerical-tolerance
tags:
  - cluster/aero-strips
  - class/numerical-tolerance
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Strip viscous drag coefficient

**Definition.** Hardcoded zero because the VLM is inviscid.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
"cdv": 0.0,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:294` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.cdv` · `frontend/hooks/useStripForces.ts (typed, not plotted)`

**Source.** 🟢 SOURCED

> AeroSandbox docs_aero_3d.md, VortexLatticeMethod: 'Pure inviscid potential flow — VLM has no viscous drag'; Anderson, Fundamentals of Aerodynamics 6e, §5.5
>
> — via `aerosandbox-expert, aerodynamics-expert`

**The source states it as.**

```
Potential-flow lifting-surface theory produces no skin-friction or pressure drag
```

**⚠️ Divergence from the source.** The zero is physically correct for the method. The defect is API-level: the AVL path fills the same field with a real CDV_LSTRP (Avl/src/aoutput.f:313), so a consumer cannot tell 'this solver has no viscous model' from 'this strip has negligible viscous drag'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** At 0.5-15 kg the wing chord Reynolds number is 5e4-3e5, where profile drag is the DOMINANT wing drag component, not a correction. A strip table that structurally reports cdv = 0 is missing the larger of the two terms for this class.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** A structural zero is indistinguishable in the API from a computed value — the AVL path fills the same field with real viscous drag.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:292-294`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
