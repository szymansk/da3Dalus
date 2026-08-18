---
name: cm-delta-e
symbol: Cm_δe
kind: quantity
unit: 1/rad
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Elevator authority (sign-enforced)

**Definition.** Elevator authority forced positive per the TE-UP sign convention; the value reported to the API.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cm_delta_e = _cm_delta_e_for_asb_path(
    cm_delta_e_raw=abs(cm_delta_e_raw),  # Enforce positive convention
    elevator_role=elevator_role,
)
```

**Inputs.**

- [[cm-delta-e-raw|Elevator authority (finite difference)]]

**Produced by.** `app/services/elevator_authority_service.py:724` — `_compute_forward_cg_limit_asb`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Net nose-up moment coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:749,766,776,786,830 (ForwardCGResult.cm_delta_e)` · `app/schemas/forward_cg.py:64` · `app/api/v2/endpoints/aeroplane/forward_cg.py:99`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.2 Eq. 12.51 (as above) and §12.5.4 ("Up-deflection is negative by convention"; C_mδE negative because positive/down elevator gives nose-down moment).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mδE = −C_Lα_h · η_h · V̄_H · (b_E/b_h) · τ_e — sign follows from the geometry, it is not imposed
```

**⚠️ Divergence from the source.** In Sadraey the sign of C_mδE is an OUTPUT of the geometry (Eq. 12.51 is negative because C_Lα_h, η_h, V_H, b_E/b_h and τ_e are all positive). The code imposes it with abs() (elevator_authority_service.py:724). When the solver returns a nose-DOWN elevator moment — which, per Eq. 12.51, can only mean the geometry is wrong (e.g. tail ahead of cg, inverted deflection sign) — the code logs a warning and proceeds with the magnitude, computing a forward CG limit from a value it knows is physically wrong. No DesignWarning reaches the user (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** abs() silently flips a physically wrong sign into a plausible one: when the elevator produces a nose-DOWN moment (a real geometry defect) the code logs a warning at 714-721 and then proceeds with the magnitude, so the forward CG limit is computed from a value known to be wrong (ADR 0020 — the substitution never reaches the user as a DesignWarning).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# ASB 3D path: use directly (NO cos² correction — Amendment B4)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
