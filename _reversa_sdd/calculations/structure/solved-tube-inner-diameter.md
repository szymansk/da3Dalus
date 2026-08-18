---
name: solved-tube-inner-diameter
symbol: Di
kind: quantity
unit: mm
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

# Solved tube inner diameter

**Definition.** Largest bore that still meets the required section modulus at the fixed outer diameter Da.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
Di = discriminant**0.25
```

**Inputs.**

- [[tube-solve-discriminant|Tube inner-diameter discriminant]]

**Produced by.** `app/services/spar_sizing.py:146` — `_solve_tube`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Strength bore from tube sizing` · `Solved tube wall thickness` · `Tube cross-section area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:147` · `app/services/spar_sizing.py:148` · `cad_designer/airplane/geometry/spar_solver.py:510` · `cad_designer/airplane/geometry/spar_solver.py:632`

**Source.** 🟡 PARTIAL

> No source. Algebraic inversion of W = π(Da⁴−Di⁴)/(32·Da) for Di, which is itself unattributed (see `section-modulus-tube`).
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
