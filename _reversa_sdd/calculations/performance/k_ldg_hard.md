---
name: k_ldg_hard
symbol: K_LDG
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Landing ground-roll coefficient

**Definition.** Base landing ground-roll coefficient for a dry hard runway at μ_brake = 0.4.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.5847`

**Formula — as the code writes it.**

```
_K_LDG_HARD: float = 0.5847
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:85` — `_K_LDG_HARD`

**Consumed by.**

- in this graph: `Friction-adjusted landing coefficient` · `Landing constraint W/S_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_s_ldg_ground:263` · `matching_chart_service._landing_constraint:341` · `matching_chart hover_text:910`

**Source.** 🔴 NO SOURCE FOUND

> The FORM is sourced (Scholz 05_PreliminarySizing §5.1 / exam-matching-chart-design-point; Sadraey §4.3.2): V_S = sqrt(2(W/S)/(rho*CL_max_L)), V_TD = k*V_S, s_ground = V_TD^2/(2*mu*g) => s = k^2/(mu*g) * (W/S)/(rho*CL_max_L). The VALUE 0.5847 is in no source.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
K_LDG = k^2/(mu_brake*g)
```

**⚠️ Divergence from the source.** Two hard findings. (1) The correct coefficient at the code's own stated k = 1.3 and mu = 0.4 is 1.3^2/(0.4*9.81) = 0.4307, not 0.5847. Inverting 0.5847 implies V_TD = 1.514*V_S, which is not a standard touchdown speed - it is the residue of the Cessna fit. (2) K_LDG = k^2/(mu*g) has units s^2/m, not dimensionless; it only looks dimensionless because g has been dropped from the denominator relative to the takeoff formula. The docstring's stated derivation is not reproducible, confirming the inventory's 'magic number' anomaly.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Validated only at 1088 kg / 16.17 m^2 (Cessna 172N). No 0.5-15 kg validation cited anywhere (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The stated derivation is not dimensionally reproducible as written (V_TD²/(2gμ)·CL/(W/S) is not dimensionless), so 0.5847 is effectively a magic number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Landing ground-roll coefficient (Roskam §3.4, V_TD = 1.3·V_S, μ_brake = 0.4) Derived: K_LDG = V_TD² / (2 g μ_brake) · C_L_max / (W/S) normalisation → 0.5847"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
