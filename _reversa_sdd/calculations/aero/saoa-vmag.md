---
name: saoa-vmag
symbol: Vmag
kind: quantity
unit: m/s
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/divergence
---

# Local velocity magnitude

**Definition.** Magnitude of the induced+freestream velocity sampled at each vortex centre.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_local = np.array(ll.get_velocity_at_points(ll.vortex_centers)); vmag = np.linalg.norm(v_local, axis=1)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:276` — `compute_section_aoa`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Section lift coefficient (Kutta-Joukowski)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md, LiftingLine.get_velocity_at_points (induced + freestream); Anderson, Fundamentals of Aerodynamics 6e, §5.1 (local relative wind = V_inf combined with downwash w)
>
> — via `aerosandbox-expert, aerodynamics-expert`

**The source states it as.**

```
V_eff = V_inf + w, magnitude |V_eff|
```

**⚠️ Divergence from the source.** Sampling get_velocity_at_points AT the vortex centres evaluates the induced-velocity kernel at the singular point of its own bound vortex; ASB regularises this with vortex_core_radius (default 1e-8 m), a length far below RC panel scale, so the self-induced contribution is numerically delicate. No source endorses sampling at the bound-vortex location.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:275-276`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
