---
name: cref-echo
symbol: c_ref
kind: quantity
unit: m
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Reference chord echo

**Definition.** Reference chord read from the solver result and echoed in the strip-forces response.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cref = float(avl_result.get("Cref", 0) or 0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1746` — `_build_strip_forces_response`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `StripForcesResponse.cref` · `frontend useStripForces`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (C_M = M/(q_inf·S·l), reference length l); AeroSandbox docs_aero_3d.md 'Return Value Conventions' (Cm = m_b/(q·S_ref·c_ref))
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
C_m = M/(q·S·c_ref), c_ref = mean aerodynamic chord
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
