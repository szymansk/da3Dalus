---
name: s-h-area-approx
symbol: S_H
kind: quantity
unit: m²
cluster: stability
user_visible: false
source_status: SOURCED
---

# Horizontal tail area (trapezoidal approximation)

**Definition.** Planform area of the horizontal tail from trapezoidal integration of its cross-sections, doubled when symmetric.

**Formula — as the code writes it.**

```
span_seg = (dy**2 + dz**2) ** 0.5
total += 0.5 * (c0 + c1) * span_seg
...
return total * (2.0 if symmetric else 1.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:476` — `_wing_area_approx`

**Consumed by.**

- in this graph: [[s-v-area-approx|Vertical tail area (trapezoidal approximation)]] · [[v-h-current|Horizontal tail volume coefficient]]
- outside it: `app/services/tail_sizing_service.py:401,414,431,441,462` · `app/services/tail_sizing_service.py:227 (V_H)`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 07_WingDesign §7.1 / wing-area-reference-definitions — trapezoidal planform reference area from chord and span segments. Sadraey §6.7.1 uses S_h as the horizontal-tail planform area in V̄_H. Lennon Ch. 7 and rcplanedesigner.com both specify that 'horizontal tail area' means the COMPLETE tail: fixed stabiliser plus elevator.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
S = Σ ½·(c_i + c_{i+1})·Δy, summed over panels, doubled for the symmetric half-model
```

**⚠️ Divergence from the source.** Correct for a symmetric horizontal tail. Wrong for a vertical fin, which is routed through the SAME function (tail_sizing_service.py:431/441) with `getattr(wing, "symmetric", True)` defaulting to doubling — a single centreline fin's area is silently reported at 2×. sm_sizing_service._find_main_wing._approx_area:830 computes the same trapezoidal area WITHOUT the symmetry factor, so the app holds two wing-area producers differing by exactly 2×.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** `getattr(wing, "symmetric", True)` defaults to doubling — for a vertical fin (also passed through this same function at line 431/441) that is wrong by 2×. sm_sizing_service._find_main_wing._approx_area:830 computes the same thing WITHOUT the symmetry factor: two producers of wing area that differ by exactly 2×.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"""Rough trapezoidal area from x_secs chord and span segments."""`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
