---
name: v-h-current
symbol: V_H
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
  - flag/divergence
---

# Horizontal tail volume coefficient

**Definition.** Non-dimensional measure of horizontal tail effectiveness: tail area × arm, normalised by wing area × MAC.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_h = (s_h_m2 * l_h) / (s_ref_m2 * mac_m)
```

**Inputs.**

- [[s-h-area-approx|Horizontal tail area (trapezoidal approximation)]]
- [[l-h-m|Horizontal tail moment arm]]

**Produced by.** `app/services/tail_sizing_service.py:227` — `compute_tail_volumes`

**Consumed by.**

- in this graph: `Tail volume classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:228,247,268,272,277` · `app/api/v2/endpoints/aeroplane/tail_sizing.py:81` · `frontend/hooks/useTailSizing.ts:19` · `frontend/components/workbench/TailVolumeCard.tsx:239` · `frontend/lib/metricsAdapters.ts:560,581`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2 Eq. 11.20 and §6.7.1: V̄_H = (S_h · l_h)/(S · C̄). Scholz 15_PreSTo_EWADE2011 §1: C_V,H = S_HT·l_HT/(S_W·c_MAC). rcplanedesigner.com, "Tail — Horizontal Tail Placement and Sizing": V_h = (S_h × L_h)/(S_w × MAC). The code's citation 'Raymer 6e Eq. 6.27' could not be verified in any consulted vault, but the formula itself is confirmed by three independent sources.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
V̄_H = S_h · l_h / (S · C̄)   (Sadraey Eq. 11.20)
```

**⚠️ Divergence from the source.** Formula matches exactly. The inputs differ from the sources: S_h from a trapezoidal approximation with an unconditional symmetry doubling (see s-h-area-approx), l_h from the wing-AC convention rather than Sadraey's cg convention, and the wing MAC from ctx rather than the Scholz §7.1 integral.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `V_H = S_H · l_H / (S_w · c_ref)     (Raymer 6e Eq. 6.27)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
