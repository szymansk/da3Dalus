---
name: delta-x-wing-shift
symbol: Δx_wing
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: PARTIAL
---

# Required wing longitudinal shift

**Definition.** Longitudinal displacement of the main wing needed to reach the target static margin (positive = aft).

**Formula — as the code writes it.**

```
delta_x = delta_needed / dsm_dx  # metres (negative = move wing fwd)
```

**Inputs.** [[sm-delta-needed|SM shortfall to target]] · [[dsm-dx-wing|SM sensitivity to wing longitudinal shift]]

**Produced by.** `app/services/sm_sizing_service.py:412` — `suggest_corrections`

**Consumed by.**

- in this graph: [[predicted-sm-wing-shift|Predicted SM after wing shift]] · [[x-np-after-shift|Neutral point after wing shift]]
- outside it: `app/services/sm_sizing_service.py:425,431,446` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:85 (SmOption.delta_value)`

**Source.** 🟡 PARTIAL

> Moving the wing longitudinally to place the cg/NP relationship is a recognised design lever — Scholz, wing-fuselage-position (07_WingDesign) and Sadraey §6.7.1 (tail area vs. location trade). The specific first-order inversion Δx = ΔSM / (dSM/dx) is not stated in any consulted source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** First-order (linear) inversion of a derivative that is itself approximate; no source endorses using it unbounded. The declared safety clip _MAX_X_WING_SHIFT_MAC = 5.0 is never applied (sm_sizing_service.py:81 has no consumer), so a shift of arbitrary size can be proposed. Sadraey's method for the same goal (§6.7.1, §6.6) re-solves the trim equation rather than extrapolating a derivative.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** `_MAX_X_WING_SHIFT_MAC = 5.0` was declared (line 81) as a safety clip for exactly this value but is never referenced — the shift is unbounded.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
