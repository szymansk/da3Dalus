---
name: l-v-m
symbol: l_V
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Vertical tail moment arm

**Definition.** Distance from the wing aerodynamic centre to the vertical tail aerodynamic centre.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
x_vtail_ac_m = x_vtail_le_m + 0.25 * vtail_mac_m
l_v = x_vtail_ac_m - x_wing_ac_m
```

**Inputs.**

- [[x-wing-ac-m|Wing aerodynamic centre x]]
- [[vtail-mac-approx|Vertical tail MAC (mean chord approximation)]]

**Produced by.** `app/services/tail_sizing_service.py:224` — `compute_tail_volumes`

**Consumed by.**

- in this graph: `Recommended vertical tail area` · `Vertical tail volume coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:231,232,261,263`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1 / Eq. 6.73 — l_vt is the distance from the vertical tail aerodynamic centre to the aircraft cg, and "In the early stage, set l_v = l_vt = l_h." Scholz 15_PreSTo_EWADE2011 §1 uses l_VT in C_V,V = S_VT·l_VT/(S_W·b_W) with the wing-AC reference.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
l_v = x_AC,vtail − x_ref, with x_AC,vtail = x_LE + 0.25·c_MAC,vtail
```

**⚠️ Divergence from the source.** Same wing-AC vs. cg convention split as l_h_m, and the same MAC-vs-mean-chord issue via vtail_mac_m. l_v is not exposed on the response schema although l_h_m is.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Not exposed on the response schema even though l_h_m is — the user can see the horizontal arm but not the vertical one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
