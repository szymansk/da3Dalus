---
name: cm-ac
symbol: Cm_ac
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Aerodynamic-centre pitching moment

**Definition.** Baseline (zero-elevator) pitching moment coefficient of the aircraft, intended to be taken about the aerodynamic centre.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cm_ac = cm_baseline
```

**Inputs.**

- [[cm-baseline|Baseline pitching moment (zero deflection)]]

**Produced by.** `app/services/elevator_authority_service.py:731` — `_compute_forward_cg_limit_asb`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Net nose-up moment coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:236,310,753,765,786` · `app/services/elevator_authority_service.py:1072 (AVL twin)`

**Source.** 🟢 SOURCED

> Anderson, "Fundamentals of Aerodynamics" 6e, §4.9 (The Aerodynamic Center): the aerodynamic centre is the point about which dc_m/dα = 0; for a cambered airfoil c_m,c/4 = −π(A₁/2), constant in α. Aircraft-level equivalent: Sadraey §6.7.1, C_mo,wf = C_m,af·(AR·cos²Λ)/(AR + 2cosΛ) + 0.01·α_t (wing/fuselage pitching-moment coefficient about ac_wf).
>
> — via `aerodynamics-expert + aircraft-design-scholz`

**The source states it as.**

```
C_mo,wf = C_m,af·(AR·cos²Λ)/(AR + 2·cosΛ) + 0.01·α_t   (Sadraey §6.7.1)
```

**⚠️ Divergence from the source.** The defining property of C_m,ac is that the moment is taken about the aerodynamic centre. The code takes it about whatever xyz_ref the converter supplied — the comment at elevator_authority_service.py:729-731 claims xyz_ref is set to x_np, but xyz_ref comes from asb_airplane.xyz_ref (:595) via plane_schema.xyz_ref, whose default is [0,0,0] (app/schemas/aeroplaneschema.py:93-94). A moment about the nose datum is not C_m,ac, and the 'NP-centered trim inversion' is not NP-centered. Sadraey also offers the closed form above, which the code does not use.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The cited comment is FALSE: xyz_ref comes from asb_airplane.xyz_ref (line 595), which the converter takes from plane_schema.xyz_ref (model_schema_converters.py:825), whose default is [0,0,0] (app/schemas/aeroplaneschema.py:93-94). It is never set to x_np. The moment is therefore about the datum/CG, not the AC, so the 'NP-centered trim inversion' is not NP-centered and Cm_ac is misnamed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Get Cm_ac from baseline (zero-deflection, at x_np reference — AeroBuildup
# uses xyz_ref which we set to x_np for the stability run)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
