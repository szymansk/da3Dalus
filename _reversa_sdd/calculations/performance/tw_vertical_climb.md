---
name: tw_vertical_climb
symbol: (T/W)_VC
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Vertical-climb T/W

**Definition.** T/W needed to sustain a vertical climb, weight plus drag.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v_climb * v_climb; k = 1.0 / (math.pi * e * ar); drag_over_weight = q * cd0 / ws + ws * k / q; return 1.0 + drag_over_weight
```

**Inputs.**

- [[ws_range_mc|W/S sweep vector]]
- [[cd0_resolved|Resolved zero-lift drag]]  — *⤵ fallback*
- [[e_resolved|Resolved Oswald factor]]  — *⤵ fallback*
- [[ar_resolved|Resolved aspect ratio]]  — *⤵ fallback*
- [[v_climb_vertical|Vertical-climb speed]]
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:585` — `_vertical_climb_constraint`

**Consumed by.**

- outside it: `_build_rc_additive_constraints:1158` · `constraints 'Vertical Climb':1164` · `MatchingChartResponse.constraints`

**Source.** 🟡 PARTIAL

> Formally this is Scholz 05_PreliminarySizing §5.3 Eq. (5.13) T/(m*g) = D/W + sin(gamma) evaluated at gamma = 90 deg, giving 1 + D/W. But Eq. 5.13 is derived under L = m*g*cos(gamma) ~ m*g, i.e. the SMALL-ANGLE assumption, which fails completely at 90 deg.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
T/(m*g) = D/W + sin(gamma), derived with L ~ m*g (small gamma)
```

**⚠️ Divergence from the source.** Confirms the inventory anomaly as a real physics error. At gamma = 90 deg, L = m*g*cos(90) = 0, so the induced-drag term (W/S)*K/q must vanish; the code retains the full level-flight induced drag. The source formula is simply outside its domain of validity here - the correct vertical-climb relation is T/W = 1 + q*C_Do/(W/S) with no induced term. hover_text's 'Anderson §6.3 with gamma=90 deg' compounds this by presenting an out-of-domain extrapolation as a citation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** In a true vertical climb lift is zero, so the induced term ws*k/q should vanish; the formula nevertheless keeps the level-flight induced drag.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"T = W + D   →  T/W = 1 + D/W" ; hover_text:1174 "Anderson §6.3 with γ=90°."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
