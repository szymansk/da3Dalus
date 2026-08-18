---
name: piece-bore
symbol: ID
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Spar piece inner diameter

**Definition.** Final bore of a spar piece: the larger of the telescoping demand and the strength-permitted bore. Zero for non-tube shapes (solid sections).

**Formula — as the code writes it.**

```
bore = max(telescope_bore, strength_bore)
```

**Inputs.** [[telescope-bore|Telescoping bore demand]] · [[strength-bore|Strength-driven bore]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:425` — `plan_spar`

**Consumed by.**

- in this graph: [[min-od-for-bore|Minimum OD to carry a bore]] · [[piece-wall|Spar piece wall thickness]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:434` · `cad_designer/airplane/geometry/spar_solver.py:124` · `app/services/spar_plan_service.py:194` · `app/schemas/spar_plan.py:191` · `frontend/hooks/useSparPlan.ts:44`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Steckung", https://wiki.rc-network.de/wiki/Steckung (joint fit) and RC-Network Wiki, "Holm", https://wiki.rc-network.de/wiki/Holm (Rohrholm)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
No source gives max(telescope demand, strength-permitted bore). Both constraints are individually recognised in the RC literature; combining them by max() is the code's own synthesis.
```

**⚠️ Divergence from the source.** Additionally: the bore is overwritten in place by snap_piece_to_stock (app/services/spar_plan_service.py:194), and it is not representable in the cad_designer Spare topology, so on insert it is dropped and surfaced only as a warning. Neither behaviour has a literature basis.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Overwritten in place by snap_piece_to_stock (app/services/spar_plan_service.py:194) with a real-stock inner diameter. Also: the bore is not representable in the cad_designer Spare topology, so on insert it is dropped and surfaced only as a warning (cad_designer/airplane/geometry/spar_cad_insertion.py module docstring).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# For non-tube shapes bores stays all-zero (solid sections).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
