---
name: achieved-coefficient
symbol: —
kind: quantity
unit: – (coefficient units)
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: solver-output
tags:
  - cluster/stability
  - class/solver-output
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver/aerobuildup
---

# Achieved target coefficient

**Definition.** Value of the target aerodynamic coefficient at the converged deflection.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
achieved = _to_scalar(final_result.get(target_coeff, float("nan")))
...
achieved_value=round(achieved, 8),
```

**Inputs.**

- [[trimmed-deflection|Trimmed control deflection]]

**Produced by.** `app/services/aerobuildup_trim_service.py:276` — `trim_with_aerobuildup`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/aerobuildup_trim_service.py:333 (AeroBuildupTrimResult.achieved_value)` · `app/api/v2/endpoints/operating_points.py:216`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.5 step 15 — after computing the deflection, the produced coefficient must be evaluated and compared against the desired value ("Compare produced C_Lh against desired (step 9)"); step 14 uses lifting-line theory or CFD for that verification. Reporting the achieved coefficient at the converged deflection is the direct realisation of that check.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Verify the produced coefficient against the desired one at the solved deflection (Sadraey §12.5.5 steps 14–15)
```

**⚠️ Divergence from the source.** Sadraey's step 15 requires an explicit accept/reject on the comparison; the code reports the achieved value without one. When the coefficient is missing the default is float('nan'), which round(...,8) propagates into a JSON response as NaN (invalid JSON) — the warning at :278-282 logs but does not substitute None.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** When the coefficient is missing the default is float('nan'), which round(...,8) propagates into a JSON response as NaN (invalid JSON) — the warning at 278-282 logs but does not substitute None.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
