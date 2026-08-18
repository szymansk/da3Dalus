---
name: q-dyn
symbol: q
kind: quantity
unit: Pa
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Dynamic pressure

**Definition.** Freestream dynamic pressure used to dimensionalise the strip forces.

**Formula — as the code writes it.**

```
q_dyn = 0.5 * rho * float(resolved_op.velocity) ** 2
```

**Inputs.** [[rho-spanwise|Air density (spanwise loads)]]

**Produced by.** `app/services/analysis_service.py:2053` — `analyze_airplane_spanwise_loads`

**Consumed by.**

- in this graph: [[spanwise-bending-moment|Running bending moment]] · [[spanwise-shear|Running shear force]]
- outside it: `compute_spanwise_loads` · `SpanwiseLoadsResponse.dynamic_pressure_Pa` · `frontend AnalysisViewerPanel.tsx:880`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 ('the foundation is the dynamic pressure'); Scholz 05_PreliminarySizing §5.6.2 Eq. 5.30
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
q_inf = ½·rho_inf·V_inf²
```

**⚠️ Divergence from the source.** None — exact match, one of the few genuine closed-form physics expressions in the file.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
