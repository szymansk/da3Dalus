---
name: v_md
symbol: V_md
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Minimum-drag speed

**Definition.** Speed for best L/D at a given wing loading.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return math.sqrt(2.0 * ws / (rho * math.sqrt(cd0 / k)))
```

**Inputs.**

- [[ws_range_mc|W/S sweep vector]]
- [[cd0_resolved|Resolved zero-lift drag]]  — *⤵ fallback*
- [[e_resolved|Resolved Oswald factor]]  — *⤵ fallback*
- [[ar_resolved|Resolved aspect ratio]]  — *⤵ fallback*
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:270` — `_v_md`

**Consumed by.**

- in this graph: `Re-refined climb T/W per W/S` · `Climb constraint T/W` · `Resolved cruise speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_climb_tw_at_ws:858,862` · `v_cruise_resolved:796`

**Source.** 🟢 SOURCED

> Sadraey 2013 Eq. 4.80 §4.3.4 (sadraey-rate-of-climb-sizing): V_ROCmax = V_Dmin = sqrt( (2W/(rho*S)) / sqrt(C_Do/K) ). Character-for-character the code's implementation. Coefficient form in Scholz 05_PreliminarySizing §5.7 Eq. 5.39.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_md = sqrt( 2*(W/S) / (rho * sqrt(C_Do/K)) )
```

**⚠️ Divergence from the source.** Citation error only: the docstring credits 'Anderson 6e §6.7'. The correct attribution is Sadraey Eq. 4.80. The two docstring spellings (sqrt(CD0*pi*e*AR) vs sqrt(cd0/k)) are the same quantity; Sadraey's sqrt(C_Do/K) is canonical. Sadraey also supplies the justification the code lacks: for maximum ROC the climb speed MUST be the minimum-drag speed, which is what makes _climb_tw_at_ws's use of V_md correct rather than arbitrary. Note a third V_md producer exists in assumption_compute_service (ctx['v_md_mps']) that compute_chart also consumes (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** V_md assumes a fixed C_Do. At RC Reynolds numbers C_Do varies strongly with speed, so a single-pass V_md is weaker here than at the transport scale Sadraey addresses.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The docstring formula (√(CD0·π·e·AR)) and the code (√(cd0/k), with k=1/(π e AR)) are the same value but written inconsistently; a third V_md producer exists in assumption_compute_service (ctx['v_md_mps']) which compute_chart also consumes at line 789.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Speed for minimum drag (best L/D) — Anderson 6e §6.7. V_md = [ 2·(W/S) / (ρ · √(CD0 · π·e·AR)) ]^0.5"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
