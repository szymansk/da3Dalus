---
name: aero-spanwise--sigma-allow-positivity-guard
kind: constant
unit: MPa
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/aero-spanwise
  - class/numerical-tolerance
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
---

# σ_allow positivity guard

**Definition.** Non-positive allowable stress is rejected with a 422 rather than dividing by zero.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0`

**Formula — as the code writes it.**

```
if sigma_allow is None or sigma_allow <= 0: raise ValidationError
```

**Inputs.**

- [[sigma-allow|Allowable bending stress]]

**Produced by.** `app/services/analysis_service.py:2142` — `_compute_spar_sizing_for_surfaces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `API 422 response`

**Source.** 🔴 NO SOURCE FOUND

> Input-validation guard against division by zero; no domain source. Correctly raises 422 rather than silently substituting — the ADR-0020-conformant pattern the rest of this cluster lacks.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
