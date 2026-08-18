---
name: fit-tol-mm
kind: constant
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: WRONG_LINE
node_class: numerical-tolerance
tags:
  - cluster/structure
  - class/numerical-tolerance
  - source/no-source-found
  - audit/wrong-line
  - flag/anomaly
---

# Containment fit tolerance

**Definition.** Absolute slack on the band containment test, and the floor on the utilisation denominator so a zero-room band yields a large-but-finite ratio.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
_FIT_TOL_MM = 1e-6
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:37` — `_FIT_TOL_MM`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `38`. 

**Consumed by.**

- in this graph: `No-spar region start` · `Spar piece feasibility` · `Spar piece utilisation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:280` · `cad_designer/airplane/geometry/spar_solver.py:282` · `cad_designer/airplane/geometry/spar_solver.py:489` · `cad_designer/airplane/geometry/spar_solver.py:539` · `cad_designer/airplane/geometry/spar_solver.py:540` · `cad_designer/airplane/geometry/spar_solver.py:603` · `cad_designer/airplane/geometry/spar_solver.py:604`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (float tolerance; note the inventory's observation stands independently of provenance — the same constant serves as a geometric tolerance and as a divide-by-zero floor for utilisation, two roles with unrelated appropriate magnitudes)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Overloaded: the same constant serves as a geometric tolerance (lines 280-282, 603-604) AND as the divide-by-zero floor for utilisation (line 539). Those are unrelated roles with unrelated appropriate magnitudes.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# A tube whose required strength OD exceeds the local containment band by more than this absolute slack (mm) forces a split. Small float tolerance.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
