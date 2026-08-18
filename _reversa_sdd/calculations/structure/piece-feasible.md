---
name: piece-feasible
kind: quantity
unit: boolean
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Spar piece feasibility

**Definition.** True when the piece's outer diameter fits the tightest containment band and that band has room at all.

**Formula — as the code writes it.**

```
feasible = od <= tightest + _FIT_TOL_MM and tightest > 0
```

**Inputs.** [[piece-outer-diameter|Spar piece outer diameter]] · [[tightest-band|Tightest containment band for a piece]] · [[fit-tol-mm|Containment fit tolerance]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:540` — `_piece_from_run_with_od`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:701` · `app/services/spar_plan_service.py:265` · `app/services/spar_plan_service.py:511` · `app/schemas/spar_plan.py:234` · `app/services/spar_insert_service.py:462` · `frontend/hooks/useSparPlan.ts:64`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm, procedure step 4 — "Verify: W_available > W_required"; RC-Network Wiki, "Holm", https://wiki.rc-network.de/wiki/Holm (the section must fit the airfoil)
>
> — via `direct verification of the kirch source + rc-aircraft-designer`

**The source states it as.**

```
The source's verification step is a STRENGTH check (W_available > W_required). Geometric containment is a separate, qualitative requirement in RC-Network "Holm".
```

**⚠️ Divergence from the source.** The code's `feasible` conflates two distinct verdicts the sources keep separate, and two independent producers write the same field: the geometric containment test here, and snap_piece_to_stock (app/services/spar_plan_service.py:180, :195) which unconditionally sets feasible=True on a successful stock snap — overwriting a geometric infeasibility with a stock-availability verdict. Per the project's settled record (BR-W18, gh-1079), `feasible = True` means "does not break", never "stiff enough" — stiffness is out of scope by decision, which is worth stating in the UI wording.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two independent producers write this same field: the geometric containment test here, and snap_piece_to_stock (app/services/spar_plan_service.py:195, :180) which unconditionally sets feasible=True on a successful stock snap — overwriting a geometric infeasibility verdict with a stock-availability verdict.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `When a piece's required OD cannot be contained by its section, it is marked infeasible with a reason rather than emitting a fake feasible plan (gh-1037 #3).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
