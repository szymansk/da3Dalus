---
name: base-cg-x-default
symbol: x_cg,base,default
kind: constant
unit: m
cluster: mass
user_visible: true
source_status: PARTIAL
---

# Fallback base CG_x for scenario CG

**Definition.** Default used when the 'cg_x' design assumption row is missing; also the value returned by compute_scenario_cg when total mass is zero.

**Value.** `0.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:356` — `compute_cg_agg_for_aeroplane / compute_loading_envelope_for_aeroplane (line 411)`

**Consumed by.**

- in this graph: [[cg-agg|Aggregate CG (default scenario)]] · [[cg-loading-aft|Aft loading CG]] · [[cg-loading-fwd|Forward loading CG]] · [[scenario-cg-x|Loading-scenario CG_x]]
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
