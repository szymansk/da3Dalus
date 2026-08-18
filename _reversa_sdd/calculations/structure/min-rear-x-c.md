---
name: min-rear-x-c
kind: constant
unit: dimensionless (x/c)
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Minimum rear-spar chord location

**Definition.** Leading-edge floor: the smallest chordwise location a clamped rear spar may take. If the clearance line would fall forward of it the layout is declared infeasible rather than clamped.

**Value.** `0.05`

**Formula — as the code writes it.**

```
_MIN_REAR_X_C = 0.05
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:188` — `_MIN_REAR_X_C`

**Consumed by.**

- in this graph: [[rear-spar-x-c-clamped|Clamped rear-spar chord location]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:247` · `cad_designer/airplane/geometry/spar_solver.py:252`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. Scholz §7.4 gives a rear-spar band of 65-75% chord and Sadraey §12.4.3(4) gives the hinge-line relation, but no source read states a leading-edge floor for a clamped rear spar. 0.05 is unattributed.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Smallest chordwise location a clamped rear spar may take (never at/forward of the LE). gh-1059.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
