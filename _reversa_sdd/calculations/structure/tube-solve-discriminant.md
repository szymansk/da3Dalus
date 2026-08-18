---
name: tube-solve-discriminant
kind: quantity
unit: mm⁴
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
---

# Tube inner-diameter discriminant

**Definition.** Fourth-power quantity whose sign decides whether a tube of the given outer diameter can meet erf_W at all. Negative means a solid section would be needed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
discriminant = Da**4 - 32.0 * erf_w * Da / math.pi
```

**Inputs.**

- [[required-section-modulus|Required section modulus]]
- [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:137` — `_solve_tube`

**Consumed by.**

- in this graph: `Solved tube inner diameter`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:138` · `app/services/spar_sizing.py:146`

**Source.** 🟡 PARTIAL

> No source. This is the algebraic inversion of the tube section-modulus relation, itself PARTIAL (see `section-modulus-tube`).
>
> — via `aircraft-design-scholz + rc-aircraft-designer (neither vault contains tube beam relations)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
