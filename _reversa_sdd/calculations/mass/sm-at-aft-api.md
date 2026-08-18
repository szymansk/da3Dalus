---
name: sm-at-aft-api
symbol: SM_aft
kind: quantity
unit: fraction of MAC
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Static margin at aft loading CG (API)

**Definition.** Static margin at the aft loading CG as returned by GET /aeroplanes/{id}/cg-envelope; drives the overall classification and the error warning text.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
sm_at_aft: float | None = (x_np - cg_aft) / mac
```

**Inputs.**

- [[x-np|Neutral point]]  — *⊣ limit*
- [[cg-loading-aft|Aft loading CG]]
- [[mac|Mean aerodynamic chord (main wing)]]

**Produced by.** `app/services/loading_scenario_service.py:594` — `get_cg_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Static-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/loading_scenario_service.py:601 (classify_sm)` · `app/services/loading_scenario_service.py:620 (warning text)` · `app/services/loading_scenario_service.py:628 (CgEnvelopeRead.sm_at_aft)` · `frontend/components/workbench/LoadingScenariosCard.tsx:84`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄, at the aft cg; Eq. (11.22) x_np − x_cg > 0 identifies this as the binding case. RC form: rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin'.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Sadraey Eq. 11.18)
```

**⚠️ Divergence from the source.** Formula matches the source. Duplicate producer of sm-at-aft-ctx (loading_scenario_service.py:260), differing in rounding and in the target_sm used for classification.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of sm-at-aft-ctx (line 260).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
