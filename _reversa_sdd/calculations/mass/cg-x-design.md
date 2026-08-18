---
name: cg-x-design
symbol: x_cg
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Design CG_x (aerodynamic CG target)

**Definition.** The longitudinal CG the design targets — neutral point shifted forward by the target static margin. Written back to the 'cg_x' design assumption on every recompute; it is the CG the aircraft SHOULD have, not the CG its parts produce.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cg_x = x_np - target_sm * mac
```

**Inputs.**

- [[x-np|Neutral point]]  — *⊣ limit*
- [[target-static-margin|Target static margin]]
- [[mac|Mean aerodynamic chord (main wing)]]

**Produced by.** `app/services/assumption_compute_service.py:108` — `recompute_assumptions`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `CG-change detection epsilon`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:199-206 (update_calculated_value 'cg_x', round(cg_x, 4), source='aerobuildup')` · `app/services/assumption_compute_service.py:802 (change detection)` · `app/services/operating_point_generator_service.py:238 (xyz_ref of operating points)` · `app/services/mass_cg_service.py:228 (get_cg_comparison design_cg_x)` · `app/services/loading_scenario_service.py:356 / :411 (base_cg_x)` · `app/services/invalidation_service.py:16 (_OP_AFFECTING_PARAMS)` · `frontend design-assumptions panel (parameter 'cg_x')`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18) inverted: SM = (x_np − x_cg)/C̄ ⇒ x_cg = x_np − SM·C̄. Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 6 'CG Location' applies exactly this inversion for models: "Lennon places the power-on NP at 35 percent of MAC from the leading edge… With CG at 25 percent MAC and NP at 35 percent, the stability margin is a healthy 10 percent" — i.e. CG is positioned by subtracting the chosen margin from the NP.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
SM = (x_np − x_cg)/C̄   (Sadraey Eq. 11.18)  ⇒  x_cg = x_np − SM·C̄
```

**⚠️ Divergence from the source.** Causality is inverted relative to Sadraey. In Sadraey §11.2/§11.5 the cg is an OUTPUT of the weight build-up (Eq. 11.1) and the extrema search (Eqs. 11.14/11.15); Eq. (11.18) is then a CHECK, and when the check fails the remedy is to move components, reposition the wing, or add ballast (§11.4, §11.6.1 'Item Placement: Fixed vs. Adjustable'), not to redefine the cg. The code makes cg_x an output of the SM target and writes it back as a 'calculated' assumption with source='aerobuildup' (assumption_compute_service.py:199-206). Lennon Ch. 6 legitimises the target-first direction for models (his 'balancing act' pre-build procedure sets a design CG and then arranges the mass to reach it), so the inversion is a defensible RC design method — but it is a different quantity from Sadraey's x_cg, and the app publishes both under CG-like names. Note also this exact expression is evaluated three times in the codebase: here, at loading_scenario_service.py:112 (cg-stability-aft), and in the unreachable mass_cg_service.compute_recommended_cg:36.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the identical formula: app/services/mass_cg_service.py:36 compute_recommended_cg(np_x, mac, target_static_margin) → np_x - target_static_margin * mac. Grep across app/ (excluding tests) finds NO production caller of compute_recommended_cg — it is complete but unreachable code (ADR 0021) and a duplicate authority (ADR 0022). A third evaluation of the same expression is cg-stability-aft (loading_scenario_service.py:112).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Does NOT write cg_x: per gh-465 the cg_x assumption represents CG_aero (NP - SM × MAC, computed by assumption_compute_service)." — app/services/mass_cg_service.py:182-184`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
