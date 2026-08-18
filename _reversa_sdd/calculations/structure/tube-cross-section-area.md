---
name: tube-cross-section-area
symbol: A
kind: quantity
unit: mm²
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Tube cross-section area

**Definition.** Annular cross-section area of the sized tube, used for spar mass integration.

**Formula — as the code writes it.**

```
area = math.pi * (Da**2 - Di**2) / 4.0
```

**Inputs.** [[solved-tube-inner-diameter|Solved tube inner diameter]] · [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:148` — `_solve_tube`

**Consumed by.**

- in this graph: [[spar-mass-half|Half-span spar mass]]
- outside it: `app/services/spar_sizing.py:347` · `app/services/spar_sizing.py:356`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary plane geometry (annulus area).
>
> — via `aircraft-design-scholz + rc-aircraft-designer (neither vault contains it)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
