---
name: piece-direction-vector
kind: quantity
unit: dimensionless (unit vector)
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Spar piece direction unit vector

**Definition.** Unit direction the straight piece runs along, from its root point to its tip point. Dimensionless; never unit-scaled.

**Formula — as the code writes it.**

```
dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
n = math.sqrt(dx * dx + dy * dy + dz * dz)
if n < 1e-12:
    return (0.0, 1.0, 0.0)
return (dx / n, dy / n, dz / n)
```

**Inputs.** [[station-y-mm|Station spanwise position]] · [[station-center-z|Station centre height]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:313` — `_unit_vector`

**Consumed by.**

- in this graph: [[no-spar-from-y|No-spar region start]] · [[piece-y-end|Spar piece tip spanwise position]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:530` · `app/services/spar_plan_service.py:500` · `app/schemas/spar_plan.py:186` · `frontend/hooks/useSparPlan.ts:42`

**Source.** 🟡 PARTIAL

> No aircraft-design source. Elementary vector normalisation.
>
> — via `aircraft-design-scholz + rc-aircraft-designer (the undeclared ADR 0020 fallback — a degenerate zero-length run silently returning the spanwise unit vector (0,1,0) — has no source basis either way)`

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): a degenerate zero-length run silently returns the spanwise unit vector (0,1,0) instead of signalling that the piece has no orientation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
