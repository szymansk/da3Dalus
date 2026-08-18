---
name: combo-estimated-top-speed
symbol: estimated_top_speed_ms
kind: quantity
unit: m/s
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Estimated top speed

**Definition.** Reported as the combo's achievable top speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
estimated_top_speed_ms=round(request.target_top_speed_ms, 1)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:270` — `_evaluate_motor_battery_combo`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `frontend/hooks/usePowertrainSizingModal.ts:76`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey (2013) Eq. 4.56 gives the actual top-speed relation: (W/P)_Vmax = eta_P / [rho_o V_max^3 C_Do/(2(W/S)) + 2K/(rho sigma V_max) (W/S)] — top speed is solved from the power available, never assumed.
```

**⚠️ Divergence from the source.** Nothing is computed. The user's target_top_speed_ms is echoed back and labelled 'estimated achievable'. Sadraey Eq. 4.56 is exactly the relation that would answer whether a combo can reach that speed, and it is available from the same inputs the code already has (C_Do, K, S, eta_P, P).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NAME CONTRADICTS DEFINITION. Nothing is estimated — the user's own target_top_speed_ms is echoed back unchanged and labelled "estimated achievable". The request field target_top_speed_ms is required (gt=0) and is otherwise never used in the computation, so the sweep never checks whether a combo can actually reach the target top speed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `schema field description (app/schemas/powertrain_sizing.py:48): "Estimated achievable top speed"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
