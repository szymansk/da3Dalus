---
name: base-cg-x-default
symbol: x_cg,base,default
kind: constant
unit: m
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/mass
  - class/numerical-tolerance
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Fallback base CG_x for scenario CG

**Definition.** Default used when the 'cg_x' design assumption row is missing; also the value returned by compute_scenario_cg when total mass is zero.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:356` — `compute_cg_agg_for_aeroplane / compute_loading_envelope_for_aeroplane (line 411)`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aggregate CG (default scenario)` · `Aft loading CG` · `Forward loading CG` · `Loading-scenario CG_x`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/loading_scenario_service.py:192 (zero-mass return)` · `app/services/loading_scenario_service.py:422/423 (no-scenario envelope fallback)`

**Source.** 🟡 PARTIAL

> The DATUM is sourced, the value is not. Sadraey, M.H., Wiley 2013, §11.2 ('Coordinate System'): the recommended x reference line is "a vertical line through the foremost point of the aircraft (e.g., fuselage nose)"; Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step c: "establish a moment reference point (typically fuselage nose or wing datum)". No source gives a fallback value.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Under the sourced datum convention (x measured aft from the foremost point), x_cg = 0.0 m places the centre of gravity exactly at the nose — a physically impossible loading, and the most nose-heavy value representable. Sadraey §11.4 characterises an over-forward cg as a controllability failure ("controllability degrades until the cg passes a forward limit at which the aircraft becomes uncontrollable"), so this fallback does not fail safe; it fails to the extreme end of the envelope. It also disagrees with the app's own PARAMETER_DEFAULTS['cg_x'] = 0.15 (app/schemas/design_assumption.py:74).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Disagrees with PARAMETER_DEFAULTS['cg_x'] = 0.15 (app/schemas/design_assumption.py:74). A missing cg_x row yields 0.0 m here and 0.15 m in assumption_compute_service — an undeclared fallback that silently places the CG at the nose datum.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
