---
name: inboard-collinear-tolerance
kind: constant
unit: mm
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
---

# Root collinearity tolerance

**Definition.** Maximum difference in root-station centreline height between the two wing halves for which a single straight carry-through beam through y=0 is accepted; above it a reinforcement is required.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `5.0`

**Formula — as the code writes it.**

```
def _inboard_collinear(
    left: list[StationData], right: list[StationData], tol_mm: float = 5.0
) -> bool:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:572` — `_inboard_collinear`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:587` · `cad_designer/airplane/geometry/spar_solver.py:676`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer. RC-Network Wiki "Steckung" (https://wiki.rc-network.de/wiki/Steckung) confirms the engineering question is real — the wing-fuselage joint is "one of the most highly loaded steckung types" where "the bending moment must be efficiently transferred from one main spar to the other" — but gives no collinearity criterion and no tolerance. 5.0 mm is unattributed and decides a user-visible structural topology (continuous carry-through vs reinforcement + joiner, i.e. whether an extra part exists). The docstring also states a second condition ("and the pieces to extend symmetrically") that the code never tests.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with no source. It decides a user-visible structural topology (front_joint = 'continuous' vs 'reinforcement+joiner'), i.e. whether an extra part exists, on an unexplained 5 mm threshold. The docstring also states a second condition ('and the pieces to extend symmetrically') that the code never tests.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `A straight beam through y=0 collinear across the root requires the two inboard stations to share the centreline z (within ``tol_mm``) and the pieces to extend symmetrically.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
