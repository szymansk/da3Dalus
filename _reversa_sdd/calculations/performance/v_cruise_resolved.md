---
name: v_cruise_resolved
symbol: V_cruise
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Resolved cruise speed

**Definition.** Cruise speed from override, aircraft dict, V_md, or a polar estimate at a nominal W/S.

**Formula — as the code writes it.**

```
v_cruise = _v_md(500.0, cd0=cd0_for_est, e=e, ar=ar_for_est, rho=rho)
```

**Inputs.** [[v_md|Minimum-drag speed]] · [[cd0_resolved|Resolved zero-lift drag]] · [[e_resolved|Resolved Oswald factor]] · [[ar_resolved|Resolved aspect ratio]]

**Produced by.** `app/services/matching_chart_service.py:785` — `compute_chart`

**Consumed by.**

- in this graph: [[chart_warnings|Matching-chart design warnings]] · [[q_dynamic_pressure|Dynamic pressure]] · [[tw_cruise_constraint|Cruise constraint T/W]] · [[v_climb_vertical|Vertical-climb speed]]
- outside it: `_cruise_constraint:853` · `v_climb_vertical:1157` · `hover_text:925`

**Source.** 🟡 PARTIAL

> Sadraey 2013 §4.3.3.1 inputs gives the sourced relation between cruise and the speed used in this constraint: 'V_max ~ 1.2-1.3 V_C (cruise is performed at 75-80% thrust)'. Using V_md as a stand-in for cruise speed is NOT sourced.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_max = 1.2-1.3 * V_cruise
```

**⚠️ Divergence from the source.** Substantive, not cosmetic. V_md is the MINIMUM-DRAG speed - the best-endurance/best-ROC speed, explicitly the speed at which the aircraft is NOT cruising. Scholz 05_PreliminarySizing §5.7 (maximum-lift-drag-ratio) treats cruise as deliberately distinct from V_md and quantifies the penalty: E = 2*E_max/((V/V_md)^4 + (V/V_md)^2). Estimating V_cruise as V_md therefore systematically under-estimates cruise speed and under-states the cruise T/W requirement.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The estimate is anchored at W/S = 500 N/m^2, described as the 'approximate midpoint' of the sweep (the true midpoint of 10-1500 is 755). 500 N/m^2 is a light-GA wing loading; a 0.5-15 kg model sits at 20-150 N/m^2, so the fallback cruise speed is computed at a wing loading 3-25x too high (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** 500 N/m² is called the 'approximate midpoint' of the sweep, but the midpoint of 10–1500 N/m² is 755; and 500 N/m² is a light-GA wing loading, not an RC one (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# V_md at an approximate midpoint W/S = 500 N/m²`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
