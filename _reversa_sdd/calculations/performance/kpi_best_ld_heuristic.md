---
name: kpi_best_ld_heuristic
symbol: 1.4
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Best-L/D heuristic factor

**Definition.** Cold-start multiplier estimating best-L/D speed from stall speed.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.4`

**Formula — as the code writes it.**

```
value=round(1.4 * stall_speed_mps, 4)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:438` — `derive_performance_kpis`

**Consumed by.**

- in this graph: `KPI: best L/D speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sadraey §4.2.5.4 Eq. 4.25 gives V_Emax = V_Pmin ~ 1.2*V_s to 1.4*V_s.
>
> — via `scholz`

**The source states it as.**

```
V_md ~ 1.4 * V_s
```

**⚠️ Divergence from the source.** The cited range is real but describes the MINIMUM-POWER speed, not the minimum-drag speed — the code has taken the top of the V_Pmin band and relabelled it V_md. Sadraey §4.3 (derivation of the 1.155 = sqrt(4/3) ROC factor) fixes the true relation: V_Pmin = 0.76*V_Dmin, i.e. V_md = 3^0.25 * V_min_sink = 1.316 * V_min_sink. The code's pair (1.4, 1.2) gives a ratio of 1.167 where the parabolic polar requires 1.316. So the two heuristics are mutually inconsistent by ~13% and cannot both be right: if V_min_sink = 1.2*V_s then V_md must be ~1.58*V_s. The in-code note admitting 'wrong by up to 15% for high-AR airframes' is honest but understates it — the pair is internally contradictory before any airframe is considered.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Heuristic multiplier of V_s (1.4·V_s and 1.2·V_s) — confidence 'estimated' (gh-475 audit §4.1; this is wrong by up to 15 % for high-AR airframes and is kept only for the cold-start case where no polar has been computed yet)."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
