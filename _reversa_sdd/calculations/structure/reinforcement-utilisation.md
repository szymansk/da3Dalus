---
name: reinforcement-utilisation
kind: constant
unit: dimensionless
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

# Reinforcement utilisation (hardcoded)

**Definition.** Utilisation value assigned to the root reinforcement piece.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
utilisation=1.0,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:647` — `_reinforcement_piece`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:509` · `app/schemas/spar_plan.py:223` · `frontend/hooks/useSparPlan.ts:62`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (a hardcoded reporting value with no measurement behind it; it contradicts the documented meaning of the field it fills — app/schemas/spar_plan.py:223-228 defines utilisation as the measured fraction of the containment band, and cad_designer/airplane/geometry/spar_solver.py:533-538 computes it as od/tightest specifically to avoid "clamping to a fake 1.0")`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Contradicts the definition of the field it fills. SparPieceOut.utilisation is documented as 'Fraction of the local containment band the piece OD uses. A value >1 means no round tube strong enough fits' (app/schemas/spar_plan.py:223-228), and _piece_from_run_with_od computes it as od/tightest specifically to avoid 'clamping to a fake 1.0' (spar_solver.py:533-538). The reinforcement reports exactly that fake 1.0 — a perfectly-utilised band — without any band ever being measured.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
