---
name: tos-l-d-tripped
symbol: l_d_tripped
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# Tripped lift-to-drag ratio

**Definition.** CL divided by the turbulator-adjusted drag coefficient.

**Formula — as the code writes it.**

```
l_d_tripped = cl / cd_tripped if cd_tripped > 0 else float("nan")
```

**Inputs.** [[tos-cl-avg|Area-weighted mean section CL]] · [[tos-cd-tripped-total|Tripped total drag coefficient]]

**Produced by.** `app/services/turbulator_optimizer_service.py:345` — `compute_ld_summary`

**Consumed by.**

- in this graph: [[tos-delta-l-d|L/D improvement]]
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorOptimizerSummarySchema.l_d_tripped` · `frontend/components/workbench/TurbulatorEditDialog.tsx:340`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.1; Scholz, Flugzeugentwurf 05_PreliminarySizing §5.6.2 (E = C_L/C_D)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
L/D = C_L / C_D
```

**⚠️ Divergence from the source.** Same defect as tos-l-d-clean: profile-drag-only denominator, so the absolute value is not an aircraft L/D. It is at least internally consistent with l_d_clean, so their difference is meaningful.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:345`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
