---
name: aero_coefficients_at_trim
symbol: CL, CD, Cm
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: solver-output
tags:
  - cluster/perf-oppoints
  - class/solver-output
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver/aerobuildup
---

# Aero coefficients at the trimmed point

**Definition.** CL, CD and Cm from one extra AeroBuildup evaluation at the final trim state.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
result = asb.AeroBuildup(airplane=airplane, op_point=op, xyz_ref=airplane.xyz_ref).run(); for key in ("CL", "CD", "Cm"): val = _safe_coeff(result, key, default=math.nan); if math.isfinite(val): out[key] = round(val, 6)
```

**Inputs.**

- [[alpha_trimmed|Trimmed angle of attack]]
- [[beta_trimmed|Trimmed sideslip angle]]
- [[default_altitude_m|Default environment altitude]]  — *ε tolerance*

**Produced by.** `app/services/operating_point_generator_service.py:772` — `_aero_coefficients_at`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:353-354, 557, 571` · `frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx:61-62 (CL, CD, L/D)` · `frontend/components/workbench/OperatingPointsPanel.tsx:833-838`

**Source.** 🟢 SOURCED

> AeroSandbox 4.2 AeroBuildup class reference and 'AeroBuildup: three reference frames' — .run() returns CL, CD, Cm etc. non-dimensionalised on s_ref/c_ref/b_ref with moments about xyz_ref
>
> — via `aerosandbox-expert`

**The source states it as.**

```
CL, CD, Cm from AeroBuildup(airplane, op_point, xyz_ref).run()
```

**⚠️ Divergence from the source.** Correct use of the documented API, and passing xyz_ref explicitly is right. Two inherited problems: the coefficients are non-dimensionalised on the possibly-wrong s_ref (see s_ref), and _safe_coeff can substitute NaN→omission silently.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Populates ``trim_enrichment.aero_coefficients`` so the OP Comparison table shows CL/CD/L/D (gh-861). Non-finite values are omitted (they serialise as null per gh-815 → the table shows "—").`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
