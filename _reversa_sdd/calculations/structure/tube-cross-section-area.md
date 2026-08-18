---
name: tube-cross-section-area
symbol: A
kind: quantity
unit: mm²
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
---

# Tube cross-section area

**Definition.** Annular cross-section area of the sized tube, used for spar mass integration.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
area = math.pi * (Da**2 - Di**2) / 4.0
```

**Inputs.**

- [[solved-tube-inner-diameter|Solved tube inner diameter]]
- [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:148` — `_solve_tube`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Half-span spar mass`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:347` · `app/services/spar_sizing.py:356`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary plane geometry (annulus area).
>
> — via `aircraft-design-scholz + rc-aircraft-designer (neither vault contains it)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
