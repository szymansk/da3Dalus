---
name: tw_power_loading
symbol: (T/W)_PL
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Power-loading T/W floor

**Definition.** Minimum T/W implied by the profile's specific-power band.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return p_over_m * eta_prop / (g * v_climb)
```

**Inputs.**

- [[power_loading_table|Power-loading bands]]  — *⊣ limit*
- [[eta_prop_default|Default propeller efficiency]]  — *⤵ fallback*
- [[g_gravity|Standard gravity]]
- [[v_climb_power_loading|Climb speed for power loading]]  — *⊣ limit*

**Produced by.** `app/services/matching_chart_service.py:564` — `_power_loading_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `_build_rc_additive_constraints:1133,1135` · `constraints 'Power-Loading':1139` · `MatchingChartResponse.constraints`

**Source.** 🟡 PARTIAL

> The thrust-power relation is SOURCED: Sadraey 2013 (sadraey-propeller-aerodynamic-principles) P_available = eta_P * P_shaft = T*V, hence T = P*eta_P/V; the prop-driven ROC constraint Eq. 4.89 §4.3.4 is built on the same relation. Dividing by W = m*g gives T/W = (P/m)*eta_P/(g*V). Both unsourced inputs sit upstream: the P/m band and V_climb.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
T = P * eta_P / V  =>  T/W = (P/m)*eta_P/(g*V)
```

**⚠️ Divergence from the source.** The algebra is exact and correctly implemented; the provenance weakness is entirely in the inputs. Note also that Sadraey's own prop ROC form (Eq. 4.89) carries a 1.155 = sqrt(4/3) factor because optimal prop climb occurs at minimum-POWER speed, not minimum-drag speed - a refinement this simpler form skips.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Prop thrust at the climb speed:  T ≈ P · η_prop / V_climb. … T/W ≈ (P/m) · η_prop / (g · V_climb)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
