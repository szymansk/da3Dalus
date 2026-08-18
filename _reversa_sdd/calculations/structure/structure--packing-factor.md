---
name: structure--packing-factor
kind: parameter
unit: dimensionless
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
---

# Packing factor

**Definition.** Fraction of the local section depth the spar may occupy; the remainder is skin/glue/print clearance.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.8`

**Formula — as the code writes it.**

```
packing_factor: float = Field(
    0.8,
    gt=0,
    le=1.0,
    description=(
        "Fraction of the local airfoil thickness that the spar outer dimension "
        "may occupy. Default 0.8."
    ),
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_sizing.py:38` — `SparSizingParams.packing_factor`

**Consumed by.**

- in this graph: `Spar outer dimension` · `Station packing clearance`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:323` · `app/services/spar_sizing.py:379` · `cad_designer/airplane/geometry/spar_solver.py:761` · `frontend/lib/sparSizingHelpers.ts:118`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. Neither vault, nor the kirch "Hauptholm" page, states any fraction of local airfoil thickness a spar may occupy. The QUALITATIVE requirement is attributable (RC-Network Wiki "Holm": Holmgurte sit "at the maximum distance apart (top and bottom of the airfoil)", and insufficient web height causes spar oil-canning; Lennon Ch. 13: flanges "as far from the neutral axis as possible") — but every source pushes toward using MORE of the depth, and none quantifies the skin/glue reserve. The specific 0.8 is unattributed, is declared three times (app/schemas/spar_sizing.py:38, app/schemas/spar_plan.py:113, cad_designer/airplane/geometry/spar_solver.py:722), and is APPLIED with two different meanings (scalar multiplier vs symmetric two-sided inset).`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Declared three times with the same default: app/schemas/spar_sizing.py:38, app/schemas/spar_plan.py:113, and cad_designer/airplane/geometry/spar_solver.py:722 (function default). It is also APPLIED differently in each path — as a scalar multiplier on outer_mm (spar_sizing.py:323) vs. a symmetric two-sided inset (spar_solver.py:761). Magic number: no source cited.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Fraction of the local airfoil thickness that the spar outer dimension may occupy. Default 0.8.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
