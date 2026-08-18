---
name: root-eps
kind: constant
unit: dimensionless (span fraction)
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
---

# Root sampling epsilon

**Definition.** Span fraction used to sample the root station instead of the degenerate y_span=0 slice, which on a real loft is pinched to zero thickness.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1e-3`

**Formula — as the code writes it.**

```
_ROOT_EPS = 1e-3
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:44` — `_ROOT_EPS`

**Consumed by.**

- in this graph: `Spanwise sampling grid`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:752`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (numerical sampling epsilon for a degenerate loft slice; not an engineering quantity)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `# Span fraction used to sample the root station instead of the degenerate y_span=0 slice (gh-1037 #4). Small enough to still represent the max-moment root, large enough to land on a valid (non-pinched) section.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
