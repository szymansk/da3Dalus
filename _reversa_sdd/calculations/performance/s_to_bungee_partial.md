---
name: s_to_bungee_partial
symbol: s_partial
kind: quantity
unit: m
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Bungee partial ground roll

**Definition.** Remaining ground roll from bungee release speed up to V_LOF.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
frac_remaining = 1.0 - (v_release_mps / v_lof_mps) ** 2; frac_remaining = max(0.0, frac_remaining); return s_full * frac_remaining
```

**Inputs.**

- [[s_to_ground|Takeoff ground roll]]
- [[v_release_bungee|Bungee release speed]]
- [[v_lof|Lift-off speed]]

**Produced by.** `app/services/field_length_service.py:230` — `_compute_s_to_bungee_partial`

**Consumed by.**

- outside it: `compute_field_lengths:415`

**Source.** 🟡 PARTIAL

> The s proportional to V^2 scaling follows directly from the constant-acceleration kinematics underlying Scholz 05_PreliminarySizing §5.2 (s = V^2/(2a)). No source covers launch-assisted takeoff.
>
> — via `aircraft-design-scholz (confirmed gap)`

**The source states it as.**

```
s(V1->V2) = s_full * (1 - (V1/V2)^2) under constant acceleration
```

**⚠️ Divergence from the source.** Valid only under the same constant-acceleration assumption as the parent formula. For an electric model whose thrust decays with airspeed, the acceleration at bungee-release speed is materially lower than at standstill, so the remaining roll is under-estimated.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Uses energy method: the total ground roll is proportional to V², so the partial roll from v_release to v_lof is: s_partial = s_full · (1 − (v_release / v_lof)²)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
