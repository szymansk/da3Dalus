---
name: solved-tube-wall
symbol: t
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Solved tube wall thickness

**Definition.** Wall thickness of the sized tube; the free dimension reported as solved_mm for shape='tube'.

**Formula — as the code writes it.**

```
wall = (Da - Di) / 2.0
```

**Inputs.** [[solved-tube-inner-diameter|Solved tube inner diameter]] · [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:147` — `_solve_tube`

**Consumed by.**

- outside it: `app/services/spar_sizing.py:344` · `app/schemas/spar_sizing.py:84` · `frontend/components/workbench/SparSizingPanel.tsx:109` · `frontend/lib/sparSizingHelpers.ts:93`

**Source.** 🟡 PARTIAL

> No source states the relation. Nearest attributable context: RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the Rohrholm (tube spar) is a standard RC main-spar configuration, but the wiki gives no sizing relation.
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
