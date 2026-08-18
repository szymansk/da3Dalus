---
name: sm-at-fwd-ctx
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

# Static margin at forward loading CG (cached)

**Definition.** Static margin when the aircraft is loaded to its forward-most scenario CG, cached in assumption_computation_context.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
sm_at_fwd = round((x_np - cg_loading_fwd_m) / mac, 4)
```

**Inputs.**

- [[x-np|Neutral point]]  — *⊣ limit*
- [[cg-loading-fwd|Forward loading CG]]
- [[mac|Mean aerodynamic chord (main wing)]]

**Produced by.** `app/services/loading_scenario_service.py:259` — `enrich_context_with_cg_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/loading_scenario_service.py:267 (ctx['sm_at_fwd'])`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄, evaluated at the most-forward cg X_cg_for from §11.5 Eq. (11.15). Same definition in RC form: rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin' — "SM = (x_NP - x_CG) / MAC, positive value means CG ahead of neutral point."
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Sadraey Eq. 11.18)
```

**⚠️ Divergence from the source.** Sadraey §11.6.2 makes the forward SM the NON-critical case for stability (larger SM = more stable; the binding constraint Eq. 11.22 is at the aft cg). Its engineering value is as the CONTROLLABILITY case (§11.6.3, forward cg limited by elevator effectiveness), which is the use the code never makes of it — ctx['sm_at_fwd'] has no reader anywhere in app/ or frontend/.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO BACKEND OR FRONTEND CONSUMER of ctx['sm_at_fwd'] was found (grep across app/ and frontend/): sm_sizing_service reads sm_at_aft, cg_forward_m and cg_stability_fwd_m but never sm_at_fwd; the UI reads the API field of the same name, which get_cg_envelope recomputes independently (line 593).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"When x_np_m is not in the context (recompute hasn't run), sm_at_fwd/aft are stored as None to avoid deceptive stub values." — app/services/loading_scenario_service.py:240-241`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
