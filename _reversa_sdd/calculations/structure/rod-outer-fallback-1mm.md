---
name: rod-outer-fallback-1mm
kind: constant
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
---

# Rod sizing outer-dimension floor

**Definition.** Floor on the outer dimension passed to the rod solver when computing the strength-required OD, so a degenerate zero-depth band does not produce a nonsense feasibility verdict.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
sol = solve_dimension(shape="rod", erf_w=erf_w, outer_mm=max(band_hi - band_lo, 1.0))
```

**Inputs.**

- [[band-lo|Contained band lower bound]]  — *⊣ limit*
- [[band-hi|Contained band upper bound]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:767` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: `Station strength-required OD`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:768`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (an inline numerical guard against a degenerate zero-depth band, with no comment; it coincidentally equals NEGLIGIBLE_OD_FLOOR_MM but is a separate literal with a different meaning)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undocumented magic number: the 1.0 mm floor is inline with no comment. It coincidentally equals NEGLIGIBLE_OD_FLOOR_MM (spar_solver.py:53) but is a separate literal with a different meaning, so the two will drift apart if one is retuned.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# strength OD as the minimum solid-rod diameter meeting required W.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
