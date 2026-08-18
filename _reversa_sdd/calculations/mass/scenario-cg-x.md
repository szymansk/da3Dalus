---
name: scenario-cg-x
symbol: x_cg,scenario
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
---

# Loading-scenario CG_x

**Definition.** Longitudinal CG of one user-defined loading scenario: mass-weighted moment sum over the component tree with toggles, mass overrides and position overrides applied, plus ad-hoc items.

**Formula — as the code writes it.**

```
m = mass_ovr_map.get(cid, float(comp.get("mass_kg", 0.0) or 0.0)); x = pos_ovr_map.get(cid, float(comp.get("x_m", 0.0) or 0.0)); total_mass += m; moment_x += m * x  ...  if total_mass <= 0: return base_cg_x; return moment_x / total_mass
```

**Inputs.** [[base-mass-default|Fallback base mass for scenario CG]] · [[base-cg-x-default|Fallback base CG_x for scenario CG]]

**Produced by.** `app/services/loading_scenario_service.py:123` — `compute_scenario_cg`

**Consumed by.**

- in this graph: [[cg-agg|Aggregate CG (default scenario)]] · [[cg-loading-aft|Aft loading CG]] · [[cg-loading-fwd|Forward loading CG]] · [[scenarios-eval|Per-scenario CG list]]
- outside it: `app/services/loading_scenario_service.py:373 (compute_cg_agg_for_aeroplane)` · `app/services/loading_scenario_service.py:433 (compute_loading_envelope_for_aeroplane)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 Eq. (11.1): X_cg = ΣW_i·x_cg,i / ΣW_i = Σm_i·x_cg,i / Σm_i. Load removal (the code's toggles) is Sadraey §11.5 Eqs. (11.14)/(11.15), which subtract removed removable loads from both numerator and denominator. Same relation in Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step c ("compute mass and moment for each component, divide total moment by total mass") and in Scholz, D. et al., PreSTo (EWADE 2011) §1: x_CG = Σ(W_i·x_i)/ΣW_i.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
X_cg = ΣW_i·x_cg,i / ΣW_i = Σm_i·x_cg,i / Σm_i   (Sadraey Eq. 11.1);  x_cg2 = (Σ_{j=1..n} x_cg_j·m_j − Σ_{j=1..k1}(x_cg_j·m_j)_removed) / (Σ_{j=1..n} m_j − Σ_{j=1..k1} m_j_removed)   (Eq. 11.14)
```

**⚠️ Divergence from the source.** Two real departures. (1) Sadraey Eqs. (11.2) and (11.3) define Y_cg and Z_cg by the identical moment sum, and §11.3.2 requires all three axial ranges (y for aileron trim, z for rudder/inertia). The code loads y_m and z_m (_load_components_as_dicts, loading_scenario_service.py:324), accepts them on AdhocItem and PositionOverride, and then computes only x — the lateral and directional balance Sadraey mandates is silently discarded. (2) Sadraey §11.5 explicitly REJECTS the approach this function implements. His §11.5 sub-section 'Why Not Trial and Error' says: "Many older references suggest enumerating tens of representative loading scenarios, computing the cg from Equation (11.1) for each, and selecting the extremes. The Sadraey procedure replaces this with a deterministic seven-to-eight-step calculation that is reliable and complete — no scenario can be missed." The code enumerates user-authored scenarios; the true extremum can therefore be missed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Lateral/vertical balance is silently dropped: _load_components_as_dicts (line 324) loads y_m and z_m, AdhocItem carries y_m/z_m (app/schemas/loading_scenario.py:72-73) and PositionOverride carries y_m_override/z_m_override (lines 58-59), but compute_scenario_cg reads only x. Those inputs are accepted, stored and never used.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
