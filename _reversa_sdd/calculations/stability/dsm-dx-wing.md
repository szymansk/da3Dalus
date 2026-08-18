---
name: dsm-dx-wing
symbol: dSM/dx_wing
kind: quantity
unit: 1/m
cluster: stability
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# SM sensitivity to wing longitudinal shift

**Definition.** Analytic derivative of static margin with respect to moving the main wing aft. Positive: wing aft increases SM.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return (1.0 - a_vh) / mac_m
```

**Inputs.**

- [[alpha-vh|Tail efficiency factor]]
- [[mac-m-fallback|MAC fallback]]  — *⤵ fallback*

**Produced by.** `app/services/sm_sizing_service.py:140` — `_dsm_dx_wing`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Required wing longitudinal shift` · `Predicted SM after wing shift`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:375,378,406,412,511,530,553,601,602,679,680,882,883`

**Source.** 🟡 PARTIAL

> No consulted source states this derivative in closed form. It is a first-order differentiation of the sourced static-margin definition Sadraey §11.6.2 Eq. 11.18 combined with the tail contribution to the neutral point (Sadraey §6.7.1). The code's cited source, "Anderson §7.6 Eq. 7.41", does not exist as claimed: Anderson, "Fundamentals of Aerodynamics" 6e Chapter 7 is "Compressible Flow: Some Preliminary Aspects" (§7.6 = shock waves; Eq. 7.41 is a compressible-flow relation). Static margin, neutral point and elevator trim are in a different Anderson book — "Introduction to Flight", stability-and-control chapter (neutral point, static margin, elevator angle to trim).
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
SM = (x_np − x_cg)/c̄ (Sadraey Eq. 11.18); differentiating w.r.t. a wing translation gives the code's form only if the neutral point moves with the wing as x_NP ← x_NP + Δx·(1 − α_VH) and the cg is held fixed.
```

**⚠️ Divergence from the source.** Beyond the misattributed citation: the derivation holds the cg fixed while the wing moves. The module's own prose (_MASS_COUPLING_WARNING, sm_sizing_service.py:83-86) states the wing carries ~30 % MTOW, so the cg moves too — Sadraey §6.7.1 makes exactly this point ("Increasing tail area both moves the neutral point aft and adds weight at the rear, moving the cg aft"). The coupling is warned about in text and omitted from the formula, so the true \|dSM/dx\| is smaller than reported.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Ignores the wing-mass coupling it warns about in prose (_MASS_COUPLING_WARNING) — moving the wing also moves ~30 % of MTOW, so the true dSM/dx is smaller. The warning is text only; the formula is uncorrected.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `∂SM/∂x_wing ≈ (1 - α_VH) / MAC
(Anderson §7.6 Eq. 7.41, spec-gate A1)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
