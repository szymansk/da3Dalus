---
name: sref-echo
symbol: S_ref
kind: quantity
unit: m²
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Reference area echo

**Definition.** Reference area echoed from the solver result, default 0.

**Derived quantity.** Computed from the inputs below.

**Value.** `0`

**Formula — as the code writes it.**

```
sref=avl_result.get("Sref", 0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1756` — `_build_strip_forces_response`

**Consumed by.**

- outside it: `StripForcesResponse.sref` · `frontend useStripForces`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (reference area S, planform area for a wing); AeroSandbox docs_aero_3d.md 'Return Value Conventions'
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
C_L = L/(q_inf·S)
```

**⚠️ Divergence from the source.** Default 0 on a missing solver key is undeclared (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
