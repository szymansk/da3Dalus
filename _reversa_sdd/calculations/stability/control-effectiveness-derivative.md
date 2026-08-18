---
name: control-effectiveness-derivative
symbol: —
kind: quantity
unit: 1/rad
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Control effectiveness (state-derivative proxy)

**Definition.** Per-surface effectiveness value; for the opti/AeroBuildup path a state derivative is used in place of a true control derivative.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
effectiveness[surface_name] = ControlEffectiveness(
    derivative=round(float(deriv_value), 6),
    coefficient=coeff,
    surface=surface_name,
)
```

**Inputs.**

- [[role-coefficient-map|Role → primary coefficient map]]

**Produced by.** `app/services/trim_enrichment_service.py:212` — `compute_control_effectiveness`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:528,567` · `frontend/components/workbench/trim-interpretation/ControlAuthorityChart.tsx`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.2 defines control effectiveness through the CONTROL derivatives: C_mδE = ∂C_m/∂δ_E (Eq. 12.51), C_LδE = ∂C_L/∂δ_E (Eq. 12.52), C_Lh_δE = ∂C_Lh/∂δ_E (Eq. 12.53); §12.6.2 gives the rudder analogues C_nδR, C_yδR and §12.4 the aileron analogue C_lδA. Sadraey §12.5.2 (control-derivatives fundamentals) explicitly separates these from STATIC stability derivatives (C_mα, C_nβ, C_yβ, C_lβ), which "do not include any control surface."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mδE = ∂C_m/∂δ_E = −C_Lα_h·η_h·V_H·(b_E/b_h)·τ_e   (Sadraey Eq. 12.51)
```

**⚠️ Divergence from the source.** For the opti/AeroBuildup path the code substitutes STATE derivatives (C_mα, C_lβ, C_nβ, C_Lα) for CONTROL derivatives — the exact distinction Sadraey draws in §12.5.2. Consequences the source makes plain: all surfaces sharing an axis report the identical number, and the value is insensitive to the elevator geometry (C_E/C_h, b_E/b_h, τ_e) that Sadraey says IS the control effectiveness. The substitution is disclosed only in a docstring, never as a DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NAME CONTRADICTS DEFINITION for the ASB path: the field is labelled 'control effectiveness' but holds Cm_α / Cl_β / Cn_β / CL_α — sensitivities to STATE, not to control deflection. All surfaces sharing an axis therefore report the identical number, and the substitution is disclosed only in this docstring, never as a DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `For the opti/AeroBuildup path, we use state derivatives as a proxy for
control effectiveness since direct control derivatives aren't available.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
