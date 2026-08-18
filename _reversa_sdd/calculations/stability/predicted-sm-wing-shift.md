---
name: predicted-sm-wing-shift
symbol: SM_pred
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Predicted SM after wing shift

**Definition.** First-order prediction of the resulting static margin after applying a wing shift.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
predicted_sm = sm_at_aft + dsm_dx * delta_x_m
```

**Inputs.**

- [[sm-at-aft|Static margin at aft CG]]
- [[dsm-dx-wing|SM sensitivity to wing longitudinal shift]]
- [[delta-x-wing-shift|Required wing longitudinal shift]]

**Produced by.** `app/services/sm_sizing_service.py:680` — `_wing_shift_option`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Predicted SM change per apply`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:693` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:85,184 (SmApplyResponse.predicted_sm)`

**Source.** 🟡 PARTIAL

> First-order Taylor prediction using the code's own dSM/dx (see dsm-dx-wing). No consulted source presents a linear SM prediction for a wing shift; Sadraey §6.7.1 re-solves Eq. 6.29 each iteration instead.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** Linear extrapolation of an approximate derivative, presented to the user as a predicted static margin without an uncertainty statement. Duplicated at sm_sizing_service.py:883.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated at line 883 in apply_wing_shift — two independent producers of predicted_sm for the same lever.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
