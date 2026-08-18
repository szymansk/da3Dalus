---
name: tc-ratio
symbol: t/c
kind: quantity
unit: dimensionless
cluster: structure
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Thickness-to-chord ratio at station

**Definition.** Station thickness ratio, resolved from the tc_by_y map by exact then nearest-key lookup, falling back to 0.12. In the wired-in path the map is built from the real lofted section thickness divided by the station chord.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
tc_ratio, tc_fallback = _get_tc(tc_by_y, y_m)
```

**Inputs.**

- [[tc-fallback-ratio|Thickness-to-chord fallback ratio]]  — *⤵ fallback*
- [[tc-nearest-key-tolerance|t/c nearest-key lookup tolerance]]

**Produced by.** `app/services/spar_sizing.py:310` — `compute_spar_sizing`

**Consumed by.**

- in this graph: `Local airfoil profile thickness`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:322` · `app/services/spar_sizing.py:339` · `app/schemas/spar_sizing.py:66` · `frontend/hooks/useSparSizing.ts:21`

**Source.** 🟢 SOURCED

> RC-Network Wiki / rcplanedesigner, wing__airfoils.md §"Relative Thickness" — "Relative thickness is the ratio between the airfoil's maximum thickness and its chord length"; Scholz, Flugzeugentwurf, 07_WingDesign §7.1/§7.3; Sadraey (Wiley 2013), Eq. (7.26)
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
Relative thickness (t/c) = maximum thickness / chord.
```

**⚠️ Divergence from the source.** The DEFINITION is sourced. The lookup mechanics (exact-then-nearest-key map lookup with a 0.12 fallback) are implementation, not literature.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
