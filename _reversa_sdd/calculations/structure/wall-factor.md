---
name: wall-factor
kind: constant
unit: dimensionless
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

# Tube wall fraction fallback

**Definition.** Fraction of the outer diameter used as the piece inner diameter when strength-based tube sizing cannot solve a feasible bore.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.6`

**Formula — as the code writes it.**

```
wall_factor: float = 0.6  # piece ID = wall_factor * OD when no strength ID given
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:90` — `SparSpec.wall_factor`

**Consumed by.**

- in this graph: `Strength bore from tube sizing`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:511` · `cad_designer/airplane/geometry/spar_solver.py:635`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer. No source read gives a bore-to-OD ratio or a minimum tube wall fraction. RC-Network Wiki "Holm" addresses web/wall sizing only qualitatively ("dimensioning depends on flight loads; insufficient web height can result in spar oil-canning"). Two problems independent of provenance: the name contradicts the use (0.6 multiplies OD to give the INNER diameter, so it is a bore fraction and the wall is (1−0.6)/2 = 20% of OD), and it is an undeclared ADR 0020 fallback that fires exactly when strength demands a SOLID section — i.e. it emits a 60%-bore hollow piece in the most loaded case, with no warning.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with no source. Name contradicts use: it is called a 'wall factor' but multiplies OD to give the INNER diameter (i.e. it is a bore fraction — the wall is (1−0.6)/2 = 20 % of OD). Undeclared fallback (ADR 0020): it fires exactly when strength wants a solid section, i.e. in the most loaded case, and produces a hollow piece with no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# piece ID = wall_factor * OD when no strength ID given`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
