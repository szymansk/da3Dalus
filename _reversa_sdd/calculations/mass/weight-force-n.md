---
name: weight-force-n
symbol: W
kind: quantity
unit: N
cluster: mass
user_visible: false
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Weight force

**Definition.** Aircraft weight in newtons, used wherever a lift/level-flight balance is solved for speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
weight_n = mass_kg * g
```

**Inputs.**

- [[mass-effective|Effective aircraft mass]]  — *⤵ fallback*
- [[gravity-constant|Gravitational acceleration]]

**Produced by.** `app/services/assumption_compute_service.py:1774` — `_stall_speed (also _max_level_speed:1901, _min_drag_speed:1942, _min_sink_speed:1968)`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- outside it: `app/services/assumption_compute_service.py:1775 (V_stall)` · `app/services/assumption_compute_service.py:1905 (induced-drag term B)` · `app/services/assumption_compute_service.py:1943 (V_md)` · `app/services/assumption_compute_service.py:1969 (V_min_sink)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §10.4 ('Units'): "The gravitational constant g = 9.81 m/s² (or 32.17 ft/s²) appears explicitly, converting from mass units to weight (force) units", and the general form of every component weight equation ends in · g: W_component = (geometry term) · ρ_mat · K_ρ · (ratio terms)^exponents · g. Scholz, D., "Flugzeugentwurf" (HAW Hamburg) worked example 'Wing Loading at Landing' applies the same conversion with g = 9.81 m/s².
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
W = m · g,  g = 9.81 m/s²   (Sadraey §10.4)
```

**⚠️ Divergence from the source.** Formula matches the source exactly. The only departure is structural: the source treats g as one constant appearing in one place per equation; the code recomputes mass_kg * g independently at assumption_compute_service.py:1774, :1901, :1942 and :1968 with no shared helper.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Four independent recomputations of the same expression (lines 1774, 1901, 1942, 1968) — no shared helper.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
