---
name: bref-echo
symbol: b_ref
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
  - flag/divergence
---

# Reference span echo

**Definition.** Reference span echoed from the solver result, default 0.

**Derived quantity.** Computed from the inputs below.

**Value.** `0`

**Formula — as the code writes it.**

```
bref=avl_result.get("Bref", 0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1758` — `_build_strip_forces_response`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `StripForcesResponse.bref` · `frontend useStripForces`

**Source.** 🟢 SOURCED

> AeroSandbox docs_aero_3d.md 'Return Value Conventions' (Cl = l_b/(q·S_ref·b_ref), Cn = n_b/(q·S_ref·b_ref))
>
> — via `aerosandbox-expert`

**The source states it as.**

```
span b_ref is the length scale for the rolling and yawing moment coefficients
```

**⚠️ Divergence from the source.** Default 0 on a missing solver key is undeclared (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
