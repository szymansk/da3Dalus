---
name: l-h-m
symbol: l_H
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: SOURCED
---

# Horizontal tail moment arm

**Definition.** Distance from the wing aerodynamic centre to the horizontal tail aerodynamic centre; CG-independent, drives the V_H recommendation.

**Formula — as the code writes it.**

```
l_h = x_htail_ac_m - x_wing_ac_m
```

**Inputs.** [[x-htail-ac-m|Horizontal tail aerodynamic centre x]] · [[x-wing-ac-m|Wing aerodynamic centre x]]

**Produced by.** `app/services/tail_sizing_service.py:200` — `compute_tail_volumes`

**Consumed by.**

- in this graph: [[s-h-recommended-mm2|Recommended horizontal tail area]] · [[v-h-current|Horizontal tail volume coefficient]]
- outside it: `app/services/tail_sizing_service.py:209,227,259` · `app/api/v2/endpoints/aeroplane/tail_sizing.py:83` · `frontend/hooks/useTailSizing.ts`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 15_PreSTo_EWADE2011 §1 (Empennage module): "l_HT = distance from wing aerodynamic center to tail aerodynamic center" in C_V,H = S_HT·l_HT/(S_W·c_MAC). Corroborated at RC scale: Lennon, "Basics of R/C Model Aircraft Design" Ch. 7 — "The tail-moment arm (TMA) is the distance between the mean aerodynamic chords of wing and tail."
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
l_HT = x_AC,tail − x_AC,wing   (Scholz PreSTo §1; Lennon Ch. 7 TMA)
```

**⚠️ Divergence from the source.** None for this convention — the code matches PreSTo and Lennon exactly. Worth recording that a SECOND convention exists and is equally standard: Sadraey §6.6 and §11.6.2 Eq. 11.20 define l_h as the distance from the tail AC to the aircraft CG, and rcplanedesigner.com's tail-lever-arm envelope (≥ 2×MAC) is stated in that CG-referenced form. The code's separate l_h_eff_from_aft_cg_m is the Sadraey convention but is display-only, so the V_H that is classified against Sadraey- and Roskam-derived bands is computed with the PreSTo convention. Separately, sm_sizing_service._dsm_dsh needs exactly this quantity but reads ctx['l_h_m'] and falls back to 2.0·MAC (sm_sizing_service.py:157-160) — the real value computed here is never published into that context.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** sm_sizing_service._dsm_dsh needs exactly this quantity but reads ctx['l_h_m'] and falls back to 2.0·MAC (sm_sizing_service.py:157-160) — the real value computed here is never written into the assumption context, so the two services never share it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `l_h_m               — wing-AC → tail-AC   (drives recommendation, CG-independent)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
