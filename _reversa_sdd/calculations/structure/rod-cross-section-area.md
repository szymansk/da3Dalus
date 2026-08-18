---
name: rod-cross-section-area
symbol: A
kind: quantity
unit: mm²
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Rod cross-section area

**Definition.** Circular cross-section area of the solved rod, used for spar mass integration.

**Formula — as the code writes it.**

```
area = math.pi * d**2 / 4.0
```

**Inputs.** [[solved-rod-diameter|Solved rod diameter]]

**Produced by.** `app/services/spar_sizing.py:170` — `_solve_rod`

**Consumed by.**

- in this graph: [[spar-mass-half|Half-span spar mass]]
- outside it: `app/services/spar_sizing.py:347` · `app/services/spar_sizing.py:356`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary plane geometry (circle area).
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**⚠️ Anomaly.** Duplicated literal expression at spar_sizing.py:167 for the infeasible branch — the same area is computed twice from two code sites.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
