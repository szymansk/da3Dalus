---
name: vs_clean
symbol: V_s1
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Clean stall speed reference

**Definition.** Clean-configuration stall speed used to seed every clean operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
vs_clean_ctx = _pick("v_s1_mps") or _pick("v_stall_mps"); if vs_clean_ctx is None: vs_clean = max(3.0, cruise / min_margin_clean) ... return {"vs_clean": max(3.0, vs_clean), ...}
```

**Inputs.**

- [[cruise_speed_resolved|Resolved cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:346` — `_estimate_reference_speeds`

**Consumed by.**

- in this graph: `Reference-speed provenance` · `Vx target speed` · `Vy target speed` · `loiter_endurance target speed` · `max_range target speed` · `stall_near_clean target speed` · `Stall speed in the turn` · `Turn target speed` · `Landing-config stall speed reference` · `Takeoff-config stall speed reference`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:401, 426, 434, 450, 458, 493, 504` · `app/services/operating_point_generator_service.py:1154 (_apply_turn_feasibility)` · `app/services/add_turn_service.py:51`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.2, Eq. 4.30–4.31: W = ½ρV_s²S·CL_max ⇒ (W/S)_Vs = ½ρV_s²CL_max
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_S1 = sqrt(2·(W/S)/(ρ·CL_max,clean))
```

**⚠️ Divergence from the source.** When a polar exists the app reads V_S1 from it — correct and sourced. The cold-start branch V_s = cruise/min_margin_clean inverts a speed-margin rule to manufacture a stall speed; that is circular (the margin is defined relative to V_s) and has no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `these are the **physics-derived** stall speeds ``√(2·m·g / (ρ·S·C_L_max_cfg))`` cached by ``assumption_compute_service`` after one ``AeroBuildup`` pass per configuration. ... The historical 0.95 / 0.90 multipliers are **not** applied because they have no physical basis (audit §5.5).`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
