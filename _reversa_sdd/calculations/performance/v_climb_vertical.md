---
name: v_climb_vertical
symbol: V_VC
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Vertical-climb speed

**Definition.** Speed used for the vertical-climb drag term, taken as the cruise speed.

**Formula — as the code writes it.**

```
v_climb_vc = max(v_cruise, 1.0)
```

**Inputs.** [[v_cruise_resolved|Resolved cruise speed]]

**Produced by.** `app/services/matching_chart_service.py:1157` — `_build_rc_additive_constraints`

**Consumed by.**

- in this graph: [[tw_vertical_climb|Vertical-climb T/W]]
- outside it: `tw_vertical_climb:1159` · `hover_text:1173`

**Source.** 🔴 NO SOURCE FOUND

> No source. Neither Scholz nor Sadraey models a sustained vertical climb; the nearest constructs (Sadraey Eq. 4.79-4.80 ROC, Eq. 4.89 prop ROC) prescribe V_Dmin or minimum-power speed, neither of which is cruise speed.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Using cruise speed as the vertical-climb speed is an arbitrary substitution with no independent input available. Combined with the retained induced-drag term, the vertical-climb line has neither a correct speed nor a correct polar.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Uses cruise speed as the vertical-climb speed — no independent 3D-vertical-line speed input exists.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Curve as a function of W/S — slight slope because D/W varies with W/S.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
