---
name: reinforcement-root-od
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Reinforcement outer diameter

**Definition.** Outer diameter of the short collinear root reinforcement, sized to the larger of the two halves' root strength-required ODs.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
root_od = max(left[0].required_od, right[0].required_od)
```

**Inputs.**

- [[station-required-od|Station strength-required OD]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:617` — `_reinforcement_piece`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Reinforcement half-reach`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:621` · `cad_designer/airplane/geometry/spar_solver.py:626` · `cad_designer/airplane/geometry/spar_solver.py:643` · `app/services/spar_plan_service.py:646`

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §7.9.3 — "the wing lift force generates a large bending moment at the wing/fuselage attachment... the wing carry-through structure must be designed to minimize bending stress and stress concentration"; RC-Network Wiki, "Steckung", https://wiki.rc-network.de/wiki/Steckung
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Both sources establish that the root reinforcement is sized to the root bending moment. No source gives max(left root required_od, right root required_od).
```

**⚠️ Divergence from the source.** Sizing to the root moment matches both sources. But unlike every other piece, the reinforcement's OD is never tested against the containment band (_max_od_for_run is not called), so it is emitted with feasible defaulting to True even when it cannot physically fit the root section — which directly violates the kirch procedure's step 4 verification and Sadraey's "minimize stress concentration" intent.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No containment check: unlike every other piece, the reinforcement's OD is never tested against the band (_max_od_for_run is not called), so it is emitted with feasible defaulting to True (SparPiece.feasible default, spar_solver.py:115) even when it cannot physically fit the root section.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Sized to the root moment (largest required OD across both root stations), placed through y=0 along the centreline, spanning a short symmetric overlap into each half.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
