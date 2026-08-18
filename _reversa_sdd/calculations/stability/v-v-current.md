---
name: v-v-current
symbol: V_V
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Vertical tail volume coefficient

**Definition.** Non-dimensional measure of vertical tail effectiveness: fin area × arm, normalised by wing area × span.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_v = (s_v_m2 * l_v) / (s_ref_m2 * b_ref_m)
```

**Inputs.**

- [[s-v-area-approx|Vertical tail area (trapezoidal approximation)]]
- [[l-v-m|Vertical tail moment arm]]

**Produced by.** `app/services/tail_sizing_service.py:232` — `compute_tail_volumes`

**Consumed by.**

- in this graph: `Tail volume classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:233,253,284,288,293` · `app/api/v2/endpoints/aeroplane/tail_sizing.py:82` · `frontend/hooks/useTailSizing.ts`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1: V̄_V = (S_v · l_v)/(S · b), with the explicit rationale that the denominator uses wing SPAN (not MAC) because the vertical tail's moment is about the z-axis. Scholz 15_PreSTo_EWADE2011 §1: C_V,V = S_VT·l_VT/(S_W·b_W). The code's 'Raymer 6e Eq. 6.28' citation is unverified but the formula is confirmed by both sources above.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V̄_V = S_v · l_v / (S · b)
```

**⚠️ Divergence from the source.** Formula matches. S_v is taken from _wing_area_approx, which doubles the area whenever `symmetric` is truthy and defaults `getattr(wing, "symmetric", True)` — so a single centreline fin has its area, and hence V_V, silently doubled unless the model explicitly sets symmetric=False (tail_sizing_service.py:491-492).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** s_v_m2 comes from _wing_area_approx, which doubles the area when `symmetric` is truthy (tail_sizing_service.py:491-492). A vertical fin defaults to symmetric=True via `getattr(wing, "symmetric", True)`, so a single fin's area — and hence V_V — is silently doubled unless the model explicitly sets symmetric=False.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `V_V = S_V · l_V / (S_w · b_ref)     (Raymer 6e Eq. 6.28)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
