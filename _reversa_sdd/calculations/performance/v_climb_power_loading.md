---
name: v_climb_power_loading
symbol: V_climb
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Climb speed for power loading

**Definition.** Climb speed assumed as 1.3·V_stall, clamped to at least 1 m/s.

**Formula — as the code writes it.**

```
v_climb = max(1.3 * max(v_stall, 1.0), 1.0)
```

**Inputs.** [[mode_default_v_s_target|Mode default stall-speed target]]

**Produced by.** `app/services/matching_chart_service.py:563` — `_power_loading_constraint`

**Consumed by.**

- in this graph: [[tw_power_loading|Power-loading T/W floor]]
- outside it: `tw_power_loading:564`

**Source.** 🟡 PARTIAL

> 1.3*V_S is sourced, but as an APPROACH speed (CS 25.125) and as the upper end of the takeoff-speed band (Sadraey Eq. 4.72: V_TO = 1.1-1.3 V_s). Sadraey Eq. 4.80 §4.3.4 states that the correct CLIMB speed is V_Dmin (= V_md), not a multiple of V_S.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey Eq. 4.80: V_climb for max ROC = V_Dmin = sqrt(2(W/S)/(rho*sqrt(C_Do/K)))
```

**⚠️ Divergence from the source.** The code attributes 1.3 to a 'Sadraey ground-roll convention' and then uses it as a climb speed. Sadraey has no such ground-roll convention (his ground roll uses V_R ~ 1.1-1.2 V_s, Eq. 4.72), and his climb-speed answer is V_md. The module already computes V_md correctly elsewhere (_v_md), so the sourced quantity is available and unused here. Additionally: double clamp with two magic 1.0 m/s floors and no warning when either fires (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Double clamp with two magic 1.0 floors and no warning when either fires (ADR 0020); the 1.3 factor is attributed to Sadraey's *ground-roll* convention but used here as a climb speed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Climb speed:  V_climb ≈ 1.3 · V_stall (Sadraey ground-roll convention).`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
