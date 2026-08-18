---
name: target-static-margin
symbol: SM_target
kind: parameter
unit: fraction of MAC (UI label '% MAC')
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: NOT_VERIFIED
node_class: user-input
tags:
  - cluster/mass
  - class/user-input
  - source/partial
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Target static margin

**Definition.** User-chosen design static margin as a fraction of MAC. Pure design choice — never auto-calculated (DESIGN_CHOICE_PARAMS).

**User input.** Supplied from outside the calculation (assumption store or request), not derived.

**Value.** `0.12 (app/schemas/design_assumption.py:75)`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/assumption_compute_service.py:107` — `recompute_assumptions (_load_effective_assumption)`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Aft CG stability limit` · `Design CG_x (aerodynamic CG target)` · `Static-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:108 (cg_x)` · `app/services/assumption_compute_service.py:473 (compute_stability_envelope)` · `app/services/assumption_compute_service.py:726 (ctx['target_static_margin'])` · `app/services/loading_scenario_service.py:112 / :585-601` · `app/services/invalidation_service.py:23 (_RECOMPUTE_TRIGGERING_PARAMS)` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:74` · `app/schemas/mass_cg.py:21` · `frontend design-assumptions panel`

**Source.** 🟡 PARTIAL

> The QUANTITY is sourced: Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄. The DEFAULT VALUE 0.12 is bracketed but not stated by: rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin' (Trainer 5/10/15% MAC, Sport 3/4/5%, Acrobatic 0/1.5/3%); Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 6 (CG 25% MAC vs NP 35% MAC ⇒ 10% margin; minimum 5%); Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 ("typically 5–10% of MAC").
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Sadraey Eq. 11.18)
```

**⚠️ Divergence from the source.** 0.12 is ABOVE the upper end of every academic band found (Scholz: 5–10% MAC; Sadraey §11.4 puts conventional aircraft 2–3% MAC from the NP at the unstable boundary and gives class cg ranges, not SM targets) and above every RC mission except Trainer, where 12% sits between the 10% average and the 15% maximum. It is therefore attributable as a conservative trainer-class choice but not as a general default. Two further defaults exist for the same parameter — 0.08 (loading_scenario_service.py:585) and 0.10 (sm_suggestions.py:74) — and unlike its neighbours power_to_weight and prop_efficiency, PARAMETER_DEFAULTS['target_static_margin'] carries no source comment (app/schemas/design_assumption.py:75), which is an ADR 0023 gap in its own right.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three divergent defaults for the same parameter — 0.12 (PARAMETER_DEFAULTS), 0.08 (loading_scenario_service.py:585), 0.10 (sm_suggestions.py:74).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Design-choice parameters (target_static_margin, g_limit) never [get a calculated value]" — app/services/design_assumptions_service.py:267`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
