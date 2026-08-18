---
name: telescope-clearance-mm
kind: constant
unit: mm
cluster: structure
user_visible: false
source_status: PARTIAL
---

# Telescoping radial clearance

**Definition.** Radial clearance at a telescoping joint: the tip-side piece OD must be this much smaller than the root-side piece bore to slide in (glue gap / slip fit).

**Value.** `0.5`

**Formula — as the code writes it.**

```
telescope_clearance_mm: float = 0.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:95` — `SparSpec.telescope_clearance_mm`

**Consumed by.**

- in this graph: [[min-od-for-bore|Minimum OD to carry a bore]] · [[telescope-bore|Telescoping bore demand]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:423` · `cad_designer/airplane/geometry/spar_solver.py:426`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Steckung (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Steckung — "The sleeves and inserts for steckung tubes are precision-fit components that must maintain tight tolerances to ensure adequate load transfer while remaining easy to assemble and disassemble."
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The source states the REQUIREMENT (precision fit, tight tolerance, load transfer vs assembly ease) but gives NO numeric clearance.
```

**⚠️ Divergence from the source.** 0.5 mm is unattributed. Independent of provenance: the field is declared as a RADIAL clearance but is applied as 2.0 × clearance on diameters at both cad_designer/airplane/geometry/spar_solver.py:423 and :426, i.e. a 1.0 mm diametral clearance — the arithmetic is self-consistent but the docstring's "at least this much smaller" reads as a diameter difference and would mislead a reader into halving it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no source. Declared as a RADIAL clearance but applied as 2.0 * clearance on diameters at both line 423 and 426, i.e. as a diametral clearance of 1.0 mm — consistent arithmetic, but the docstring's 'at least this much smaller' reads as a diameter difference and would mislead a reader into halving it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Radial clearance (mm) at a telescoping joint: the tip-side piece OD must be at least this much smaller than the root-side piece bore so it can slide in (glue gap / slip fit). gh-1037.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
