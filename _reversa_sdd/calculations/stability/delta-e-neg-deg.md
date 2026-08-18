---
name: delta-e-neg-deg
symbol: δe
kind: quantity
unit: deg
cluster: stability
user_visible: false
source_status: SOURCED
---

# TE-UP deflection command

**Definition.** Negative (trailing-edge-up) elevator deflection sent to the solver for the finite-difference Cm_δe run.

**Formula — as the code writes it.**

```
delta_e_neg_deg = -abs(float(delta_e_max_rad * 180.0 / math.pi))
```

**Inputs.** [[delta-e-max-rad|Maximum elevator deflection (radians)]]

**Produced by.** `app/services/elevator_authority_service.py:611` — `_compute_forward_cg_limit_asb`

**Consumed by.**

- in this graph: [[cm-delta-e-raw|Elevator authority (finite difference)]]
- outside it: `app/services/elevator_authority_service.py:696 (with_control_deflections)` · `app/services/elevator_authority_service.py:1016,1055,1085 (AVL twin)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.4: "Up-deflection is negative by convention"; §12.5.5 worked example gives δ_Emax_up = −25°. The trailing-edge-up direction is the one that produces nose-up pitch and therefore governs the forward-cg/rotation case (§11.6.3).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_E < 0 = trailing edge up = nose-up pitching moment
```

**⚠️ Divergence from the source.** Sign convention matches. The code round-trips deg→rad→deg through _delta_e_max_rad rather than reading the source field, a needless precision hop.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Round-trips deg→rad→deg through _delta_e_max_rad instead of using the source field directly.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Convert back to degrees for AeroBuildup (negative = TE-UP)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
