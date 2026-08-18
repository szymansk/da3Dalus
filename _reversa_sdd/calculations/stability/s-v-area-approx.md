---
name: s-v-area-approx
symbol: S_V
kind: quantity
unit: m²
cluster: stability
user_visible: false
source_status: SOURCED
---

# Vertical tail area (trapezoidal approximation)

**Definition.** Planform area of the vertical tail, from the same trapezoidal helper as the horizontal tail.

**Formula — as the code writes it.**

```
s_v_m2 = _wing_area_approx(vtail)
```

**Inputs.** [[s-h-area-approx|Horizontal tail area (trapezoidal approximation)]]

**Produced by.** `app/services/tail_sizing_service.py:441` — `build_tail_sizing_context_from_aeroplane`

**Consumed by.**

- in this graph: [[v-v-current|Vertical tail volume coefficient]]
- outside it: `app/services/tail_sizing_service.py:466` · `app/services/tail_sizing_service.py:232 (V_V)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1 — S_v is the vertical-tail planform area in V̄_V = S_v·l_v/(S·b); §6.7.1 (spin-recovery discussion) treats it as the single exposed fin planform. rcplanedesigner.com, "Tail — Vertical Tail Placement and Sizing" gives total vertical tail area ≈ 35–50 % of horizontal tail area as the RC cross-check.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
S_v = exposed fin planform area (single fin, not doubled)
```

**⚠️ Divergence from the source.** Inherits the symmetric-default doubling from _wing_area_approx (see s-h-area-approx). The rcplanedesigner 35–50 % cross-check would immediately expose a doubled fin, but the code does not perform it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** See s-h-area-approx: a single vertical fin gets its area doubled by the symmetric default.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
