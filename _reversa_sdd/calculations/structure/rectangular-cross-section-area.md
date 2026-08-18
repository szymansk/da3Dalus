---
name: rectangular-cross-section-area
symbol: A
kind: quantity
unit: mm²
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
---

# Rectangular cross-section area

**Definition.** Area of the solid rectangular spar section, used for mass integration.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
area = b * h
```

**Inputs.**

- [[solved-rectangular-width|Solved rectangular width]]
- [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:183` — `_solve_rectangular`

**Consumed by.**

- in this graph: `Half-span spar mass`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:347` · `app/services/spar_sizing.py:356`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary plane geometry (rectangle area).
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
