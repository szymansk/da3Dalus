---
name: sm-at-fwd-api
symbol: SM_fwd
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

# Static margin at forward loading CG (API)

**Definition.** Static margin at the forward loading CG as returned by GET /aeroplanes/{id}/cg-envelope.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
sm_at_fwd: float | None = (x_np - cg_fwd) / mac
```

**Inputs.**

- [[x-np|Neutral point]]  — *⊣ limit*
- [[cg-loading-fwd|Forward loading CG]]
- [[mac|Mean aerodynamic chord (main wing)]]

**Produced by.** `app/services/loading_scenario_service.py:593` — `get_cg_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Static-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/loading_scenario_service.py:600 (classify_sm)` · `app/services/loading_scenario_service.py:627 (CgEnvelopeRead.sm_at_fwd)` · `frontend/components/workbench/LoadingScenariosCard.tsx:83`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄; RC statement of the same relation with the identical symbols: rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin' — "SM = (x_NP - x_CG) / MAC".
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Sadraey Eq. 11.18)
```

**⚠️ Divergence from the source.** Formula matches the source exactly. The divergence is that this is a second evaluation of sm-at-fwd-ctx (loading_scenario_service.py:259) reached with a DIFFERENT target static margin — 0.08 here (:585) versus PARAMETER_DEFAULTS 0.12 — so the API's classification of the same SM can differ from the context's. Nothing in Sadraey licenses two target margins for one aircraft.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of sm-at-fwd-ctx (same formula, line 259) using a different target_sm default (0.08 here vs. the effective assumption elsewhere).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"This prevents the old deceptive pattern of synthesising x_np = cg_x + target_sm*MAC which made sm_at_aft == target_sm always (a false-positive \"perfect\" envelope)." — app/services/loading_scenario_service.py:566-569`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
