---
name: ld-ratio-force
kind: quantity
unit: -
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
  - flag/anomaly
  - flag/divergence
---

# Glide ratio from forces

**Definition.** L/D computed from dimensional lift and drag for the glide-ratio panel.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ld_curve = np.where(np.abs(drag_curve) > 1e-12, lift_curve / drag_curve, np.nan)
```

**Inputs.**

- [[lift-force-values|Lift force array]]
- [[drag-force-values|Drag force array]]
- [[divide-guard-epsilon|Division guard epsilon]]  — *ε tolerance*

**Produced by.** `app/services/analysis_service.py:1154` — `_plot_glide_ratio`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Sweet-spot index`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `alpha-sweep PNG panel 4`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2; AeroSandbox docs_aero_3d.md 'Return Value Conventions' (CL = L/(q·S_ref), CD = D/(q·S_ref))
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
L/D = C_L/C_D — identical, since both forces are normalised by the same q·S_ref
```

**⚠️ Divergence from the source.** MATERIAL as a code defect, not a physics one: because L/D from forces and C_L/C_D are algebraically identical, panel 2 and panel 4 MUST peak at the same α. If the rendered 'Sweet Spot' and '(CL/CD)max' markers land on different indices, that is a bug (array-length mismatch from _safe_slice, or NaN handling), not two legitimate definitions.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second L/D producer in the same figure — panel 4 maximises L/D from forces while panel 2 maximises CL/CD from coefficients; the 'Sweet Spot' and '(CL/CD)max' markers can land on different alpha indices.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
