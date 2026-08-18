---
name: hyperbola-samples
symbol: _HYPERBOLA_SAMPLES
kind: constant
unit: count
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# C-rate hyperbola sample count

**Definition.** Number of points sampled along the C-rate hyperbola for the feasible-region plot.

**Value.** `40`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:75` — `_HYPERBOLA_SAMPLES`

**Consumed by.**

- in this graph: [[hyperbola-capacity-samples|Hyperbola capacity samples]]
- outside it: `app/services/powertrain_solution_space_service.py:173`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Plot resolution, no engineering content.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# Number of sample points for the feasible-region C-rate hyperbola`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
