---
name: node-scale-factor
symbol: k_scale
kind: parameter
unit: dimensionless
cluster: mass
user_visible: true
source_status: SOURCED
---

# Node weight scale factor

**Definition.** Per-node empirical multiplier applied to the density-derived CAD weight (infill, support material, print over/under-extrusion).

**Value.** `1.0 (SQLAlchemy default, app/models/component_tree.py:61; Pydantic default app/schemas/component_tree.py:57)`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:455` — `_weight_from_cad_shape (consumer); DB default in app/models/component_tree.py:61`

**Consumed by.**

- in this graph: [[cad-shape-own-weight-surface|CAD shape own weight — surface print]] · [[cad-shape-own-weight-volume|CAD shape own weight — solid print]]
- outside it: `app/services/component_tree_service.py:455` · `app/services/component_tree_service.py:457` · `app/schemas/component_tree.py:57` · `frontend/hooks/useComponentTree.ts (node write payload)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §10.4 — the "density factor K_ρ: a dimensionless empirical multiplier that captures aircraft category, configuration, and subsystem placement. Each component has its own K_ρ table." Rationale given in the same section: "aero-structures are not solid objects but hollow assemblies of skin, spars, frames, ribs, stiffeners, and longerons. A pure density-times-volume calculation would massively overestimate weight, so empirical density factors (K_ρ values) reduce the result to physically correct numbers."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
W_component = (geometry term) · ρ_mat · K_ρ · (ratio terms)^exponents · g  (Sadraey §10.4)
```

**⚠️ Divergence from the source.** The naming concern in the inventory is resolved in the code's favour: Sadraey's K_ρ is confirmed to be a LINEAR, dimensionless multiplier on a density-derived weight — exactly how scale_factor is used. The name 'scale_factor' is what misleads, not the arithmetic. Three real divergences remain: (a) Sadraey's K_ρ is TABULATED per component and per aircraft category; the code's is a free per-node user number with no table and no validation range; (b) Sadraey's K_ρ is always < 1 for hollow structures, while the code's default is 1.0 — the default is the uncalibrated case Sadraey rejects; (c) no K_ρ value for FDM-printed RC structure exists in any consulted source, so the numeric default 1.0 itself is NO_SOURCE_FOUND even though the concept is sourced.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's K_ρ tables are calibrated against his Table 10.5 sample (16 aircraft, home-built through large cargo) and Figure 10.6 (12 aircraft, 3.5 m² to 576 m² wing area). The lightest datum is a Bede BD-5B home-built at 39.5 kg wing mass — roughly 100× this app's 0.5–15 kg target. No K_ρ in the source is validated at RC/UAV scale, and none covers 3D-printed structure at all (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Named 'scale_factor' (reads as a geometric scale, which would enter volume as k³) but documented and used as a linear weight multiplier. Empirical value with no cited source (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Weight scaling factor (empirical)" — app/schemas/component_tree.py:57`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
