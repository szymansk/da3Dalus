---
name: climb_tw_picard
symbol: (T/W)_climb(W/S)
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Re-refined climb T/W per W/S

**Definition.** Climb constraint evaluated at a Reynolds-refined V_md for each W/S sample.

**Formula — as the code writes it.**

```
v_min_drag = _v_md(ws, cd0, e, ar, rho); cd0_vmd = _cd0_at_v(v_min_drag); e_vmd = _e_at_v(v_min_drag); v_min_drag_refined = _v_md(ws, cd0_vmd, e_vmd, ar, rho); return _climb_constraint(ws, gamma, v_min_drag_refined, cd0_vmd, e_vmd, ar, rho)
```

**Inputs.** [[v_md|Minimum-drag speed]] · [[tw_climb_constraint|Climb constraint T/W]]

**Produced by.** `app/services/matching_chart_service.py:857` — `_climb_tw_at_ws`

**Consumed by.**

- outside it: `climb_tw:865`

**Source.** 🟡 PARTIAL

> Evaluating the climb constraint at V_md is SOURCED: Sadraey 2013 Eq. 4.80 §4.3.4 states that for maximum ROC the climb speed must be the minimum-drag speed. The fixed single Picard pass over a Reynolds-dependent polar has no counterpart - Sadraey uses a fixed C_Do from Table 4.12 and does not iterate.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_climb = V_Dmin (Sadraey Eq. 4.80)
```

**⚠️ Divergence from the source.** Exactly one iteration, hardcoded, with no convergence check or reported residual. Additionally the refinement is inert through the API: the matching-chart endpoint never supplies polar_re_table or mac_m, so _cd0_at_v/_e_at_v always return the scalar fallback and both Picard passes give the same answer (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The Re-refinement is the one part of this cluster that is genuinely RC-motivated (low-Re polars vary strongly with speed), and it is precisely the part that is dead in production.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Exactly one Picard iteration, hardcoded, with no convergence check or reported residual.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Recompute V_md with Re-specific cd0/e (one Picard pass)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
