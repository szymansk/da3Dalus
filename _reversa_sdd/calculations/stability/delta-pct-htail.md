---
name: delta-pct-htail
symbol: Δ%
kind: quantity
unit: – (fraction)
cluster: stability
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Horizontal tail chord-scale fraction

**Definition.** Fractional chord scaling of the horizontal tail equivalent to the required area change (chord-scale preserves span).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_pct = delta_sh_m2 / s_h_m2  # fraction (negative = shrink)
```

**Inputs.**

- [[delta-sh-m2|Required horizontal tail area change]]
- [[s-h-m2-fallback|Horizontal tail area fallback]]  — *⤵ fallback*

**Produced by.** `app/services/sm_sizing_service.py:414` — `suggest_corrections`

**Consumed by.**

- in this graph: `Horizontal tail chord scale factor` · `Predicted SM after htail chord-scale`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:447` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:85,143`

**Source.** 🟡 PARTIAL

> Chord-scaling the tail at fixed span is a legitimate way to realise a target S_H — Sadraey §6.7.1 solves for S_h and §6.7 then distributes it over AR, taper, span and chord. No source prescribes chord-scale (as opposed to span-scale) as the preferred realisation.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
S_h = V_H·C̄·S/l, then S_h distributed via AR_h, λ_h, b_h, C_h (Sadraey §6.7)
```

**⚠️ Divergence from the source.** Chord-scaling at constant span changes the tail aspect ratio, which changes C_Lα_h through Sadraey Eq. 6.57 (C_Lα_h = C_lα_h/(1 + C_lα_h/(π·AR_h))). The code's own comment concedes 'AR changes proportionally' but the sensitivity dSM/dS_H that produced the number assumed a_t/a fixed — so the prediction and the applied geometry disagree. Sadraey §6.7 keeps tail AR in a 4–6 band precisely to avoid this.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Chord-scale preserves span (AR changes proportionally).`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
