---
name: rod-outer-fallback-1mm
kind: constant
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Rod sizing outer-dimension floor

**Definition.** Floor on the outer dimension passed to the rod solver when computing the strength-required OD, so a degenerate zero-depth band does not produce a nonsense feasibility verdict.

**Value.** `1.0`

**Formula — as the code writes it.**

```
sol = solve_dimension(shape="rod", erf_w=erf_w, outer_mm=max(band_hi - band_lo, 1.0))
```

**Inputs.** [[band-lo|Contained band lower bound]] · [[band-hi|Contained band upper bound]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:767` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: [[station-required-od|Station strength-required OD]]
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
