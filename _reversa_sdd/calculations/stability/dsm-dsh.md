---
name: dsm-dsh
symbol: dSM/dS_H
kind: quantity
unit: 1/m²
cluster: stability
user_visible: false
source_status: PARTIAL
---

# SM sensitivity to horizontal tail area

**Definition.** Analytic derivative of static margin with respect to horizontal tail area. Positive: larger tail increases SM.

**Formula — as the code writes it.**

```
return at_over_a * _DE_DA_FACTOR * l_h_m / (s_ref_m2 * mac_m)
```

**Inputs.** [[at-over-a-ratio|Tail-to-wing lift-curve-slope ratio]] · [[de-da-factor|Downwash factor (1 − de/dalpha)]] · [[l-h-m-fallback|Tail arm fallback]] · [[s-ref-m2-fallback|Reference area fallback]] · [[mac-m-fallback|MAC fallback]]

**Produced by.** `app/services/sm_sizing_service.py:162` — `_dsm_dsh`

**Consumed by.**

- in this graph: [[delta-sh-m2|Required horizontal tail area change]] · [[predicted-sm-fwd-htail|Predicted forward SM after htail scale]] · [[predicted-sm-htail-scale|Predicted SM after htail chord-scale]]
- outside it: `app/services/sm_sizing_service.py:376,379,407,413,512,531,565,642,646,708,709,961,963`

**Source.** 🟡 PARTIAL

> Derivable from the sourced definitions: tail volume V_H = S_H·l_H/(S·c̄) (Sadraey §11.6.2 Eq. 11.20 / §6.7.1) and the tail's contribution to the neutral point via η_h·(a_t/a)·(1 − dε/dα)·V_H (Sadraey Eq. 6.29). Differentiating w.r.t. S_H reproduces the code's form. No source states the derivative itself.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V̄_H = S_h·l_h/(S·C̄) (Sadraey Eq. 11.20); ∂/∂S_H of the tail term gives (a_t/a)(1 − dε/dα)·l_H/(S_w·C̄)
```

**⚠️ Divergence from the source.** The literature group carries the tail dynamic-pressure ratio η_h = 0.85–0.95 (Sadraey §6.7.1); the code omits it, overstating the sensitivity by ~5–15 %. It also inherits the unsourced a_t/a = 1.0 and the 0.6 downwash factor, and the fallback l_h = 2.0·MAC.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `∂SM/∂S_H = (a_t/a)·(1 - dε/dα)·l_H / (S_w·MAC)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
