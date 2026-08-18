---
name: rectangular-cross-section-area
symbol: A
kind: quantity
unit: mm²
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Rectangular cross-section area

**Definition.** Area of the solid rectangular spar section, used for mass integration.

**Formula — as the code writes it.**

```
area = b * h
```

**Inputs.** [[solved-rectangular-width|Solved rectangular width]] · [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:183` — `_solve_rectangular`

**Consumed by.**

- in this graph: [[spar-mass-half|Half-span spar mass]]
- outside it: `app/services/spar_sizing.py:347` · `app/services/spar_sizing.py:356`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary plane geometry (rectangle area).
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
