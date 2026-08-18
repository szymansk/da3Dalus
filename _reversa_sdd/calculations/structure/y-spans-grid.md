---
name: y-spans-grid
kind: quantity
unit: dimensionless (span fraction)
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - audit/confirmed
---

# Spanwise sampling grid

**Definition.** Evenly spaced span fractions root-to-tip at which the section is sampled, with the root replaced by _ROOT_EPS to avoid the degenerate pinched slice.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y_spans = np.linspace(0.0, 1.0, max(2, n_span)).tolist()
...
if y_spans and y_spans[0] <= 0.0:
    y_spans[0] = _ROOT_EPS
```

**Inputs.**

- [[n-span|Number of spanwise stations]]
- [[root-eps|Root sampling epsilon]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:745` — `build_stations_from_geometry`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Station spanwise position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:754`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (numerical sampling grid). Note the project record (gh-1136, BR-W16) documents a consequence worth carrying: with the default n_span=6 the tip station at y_span=1.0 has zero moment and is always dropped, so the reported no-spar region starts at 80% of half-span and moves to 99.5% at n_span=200 — a sampling parameter changing a user-visible structural answer.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `gh-1037 #4: the slice at y_span=0 is degenerate on a real loft (pinched, zero-thickness centreline section) and would poison the governing (max-moment) root station. Sample the root at y_span=eps instead so the root sizing uses a valid section while still representing the highest moment.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
