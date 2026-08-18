---
name: piece-utilisation
kind: quantity
unit: dimensionless
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Spar piece utilisation

**Definition.** Fraction of the tightest containment band the piece's outer diameter uses. Deliberately allowed to exceed 1 to report truthfully that no strong-enough round tube fits.

**Formula — as the code writes it.**

```
utilisation = od / max(tightest, _FIT_TOL_MM)
```

**Inputs.** [[piece-outer-diameter|Spar piece outer diameter]] · [[tightest-band|Tightest containment band for a piece]] · [[fit-tol-mm|Containment fit tolerance]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:539` — `_piece_from_run_with_od`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:509` · `app/schemas/spar_plan.py:223` · `frontend/hooks/useSparPlan.ts:62`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (a reporting ratio, not a design quantity; no source read defines a spar containment utilisation). Independent of provenance: the value goes stale after stock snapping — snap_piece_to_stock (app/services/spar_plan_service.py:193) replaces outer_d without recomputing utilisation — and _reinforcement_piece (cad_designer/airplane/geometry/spar_solver.py:647) hardcodes 1.0 with no band measured.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Becomes stale after stock snapping: snap_piece_to_stock (app/services/spar_plan_service.py:193) replaces outer_d but does not recompute utilisation, so the reported utilisation belongs to the pre-snap diameter. Also contradicted by _reinforcement_piece (spar_solver.py:647), which hardcodes utilisation=1.0 without any band computation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Honest utilisation (gh-1037 #3): the fraction of the tightest containment band the piece OD uses. It may exceed 1 when no round tube strong enough fits — we report that truthfully instead of clamping to a fake 1.0. When the band has literally no room (tightest == 0) we floor the denominator to a tiny value so the ratio is large-but-finite (JSON-serialisable) and still clearly signals infeasibility.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
