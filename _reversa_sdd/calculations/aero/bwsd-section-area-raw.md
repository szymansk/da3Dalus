---
name: bwsd-section-area-raw
symbol: section_areas[i]
kind: quantity
unit: m²
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/divergence
---

# Raw trapezoidal section area

**Definition.** Half-panel-width trapezoidal area attributed to each spanwise section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
left = (y_arr[i] - y_arr[i - 1]) / 2.0 if i > 0 else 0.0; right = (y_arr[i + 1] - y_arr[i]) / 2.0 if i < n - 1 else 0.0; section_areas[i] = chord_arr[i] * (left + right)
```

**Inputs.**

- [[saoa-y|Panel spanwise position]]
- [[saoa-chord|Panel chord]]

**Produced by.** `app/services/turbulator_optimizer_service.py:418` — `build_wing_section_data`

**Consumed by.**

- in this graph: `Normalised section area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:305 (ASTRP = WSTRIP(J) * CHORD(J), strip area = strip width x local chord)
>
> — via `avl-advisor`

**The source states it as.**

```
A_strip = chord * strip_width
```

**⚠️ Divergence from the source.** Half-distance-to-each-neighbour reproduces AVL's strip width for a uniform mesh and is the standard trapezoidal attribution. Endpoint sections get only a half-width contribution (left=0 at the root, right=0 at the tip), which under-attributes area at both ends before renormalisation.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:414-418`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
