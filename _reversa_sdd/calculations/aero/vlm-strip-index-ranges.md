---
name: vlm-strip-index-ranges
symbol: strip_ranges
kind: quantity
unit: index
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/divergence
  - solver-adjacent/vlm
---

# Panel index ranges per strip

**Definition.** [start, end) panel index ranges delimiting each chordwise strip via the trailing-edge flag.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ranges.append((start, i + 1)); start = i + 1  (for each is_trailing_edge)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:39` — `_strip_index_ranges`

**Consumed by.**

- in this graph: `Strip area` · `Per-strip force vector`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/vlm_strip_forces.py:compute_vlm_strip_forces`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:383-395 (OUTELE: each strip J owns NV chordwise elements from IJFRST(J))
>
> — via `avl-advisor`

**⚠️ Divergence from the source.** Delimiting strips by the trailing-edge flag reproduces AVL's strip/element hierarchy. Implementation, no physical formula.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:37-41`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
