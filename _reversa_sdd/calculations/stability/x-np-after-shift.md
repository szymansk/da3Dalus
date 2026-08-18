---
name: x-np-after-shift
symbol: x_NP_new
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: PARTIAL
---

# Neutral point after wing shift

**Definition.** Predicted neutral point position after the main wing is moved by delta_x.

**Formula — as the code writes it.**

```
x_np_new = x_np_m + delta_x * (1.0 - a_vh)
```

**Inputs.** [[delta-x-wing-shift|Required wing longitudinal shift]] · [[alpha-vh|Tail efficiency factor]]

**Produced by.** `app/services/sm_sizing_service.py:425` — `suggest_corrections`

**Consumed by.**

- in this graph: [[sm-at-fwd-after-shift|Forward-CG SM after wing shift]]
- outside it: `app/services/sm_sizing_service.py:426`

**Source.** 🟡 PARTIAL

> The underlying statement — that the neutral point moves with the wing but by less than the wing itself, because the tail contribution is anchored aft — follows from Sadraey §6.7.1 Eq. 6.29 / §11.6.2 Eq. 11.20 (the tail term depends on l_H, which grows as the wing moves forward). No source states the linearised form x_NP_new = x_NP + Δx·(1 − α_VH).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
x_NP = x_ac,wing + V_H·(S_W/c̄)·(dc_m/dC_L)_tail  (exam-tail-volume-coefficient, from Sadraey §6.7.1)
```

**⚠️ Divergence from the source.** The source form makes x_NP depend on V_H, which contains l_H — so moving the wing changes l_H and hence V_H nonlinearly. The code's linearisation folds all of that into the single factor (1 − α_VH), where α_VH itself omits l_H entirely.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# x_NP shifts with the wing: x_NP_new ≈ x_NP_old + delta_x * (1 − α_VH)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
