---
name: main-wing-approx-area
symbol: S_approx
kind: quantity
unit: m²
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Approximate wing area (main-wing selection)

**Definition.** Trapezoidal planform area used only to pick the largest non-tail wing as the main wing.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
span_seg = (dy**2 + dz**2) ** 0.5
total += 0.5 * (c0 + c1) * span_seg
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:841` — `_find_main_wing._approx_area`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:844 max(candidates, key=_approx_area)`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 07_WingDesign §7.1 and wing-area-reference-definitions — trapezoidal wing reference area from chord and span segments; standard planform integration.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
S = Σ ½·(c_i + c_{i+1})·Δy over the panels (trapezoidal reference area)
```

**⚠️ Divergence from the source.** The code omits the symmetry doubling that its sibling tail_sizing_service._wing_area_approx:476 applies, so the two produce areas differing by exactly 2× for the same wing. Harmless for the ranking use here, wrong if ever reused.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third independent implementation of wing area in the repo: this one (no symmetry doubling), tail_sizing_service._wing_area_approx:476 (WITH symmetry doubling), and ASB's wing.area() used by assumption_compute_service:1088. Here the omission of the symmetry factor is harmless for ranking but the two sm_sizing/tail_sizing versions differ by exactly 2× for the same wing.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Pick by approximate area (sum of chord segments × span)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
