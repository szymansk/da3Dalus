---
name: sm-max-fwd
symbol: SM_max,fwd
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
---

# Maximum forward-CG static margin

**Definition.** Largest static margin the elevator can still trim at the forward CG, derived from the forward stability limit.

**Formula — as the code writes it.**

```
sm_max_fwd: float = (x_np_m - cg_stability_fwd_m) / mac_m
```

**Inputs.** [[mac-m-fallback|MAC fallback]] · [[x-cg-fwd-trim-inversion|Forward CG limit (trim inversion)]]

**Produced by.** `app/services/sm_sizing_service.py:509` — `_suggest_corrections_fwd`

**Consumed by.**

- in this graph: [[sm-deficit-fwd|Forward-CG SM excess]]
- outside it: `app/services/sm_sizing_service.py:516,522,552,556,575,576,581`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.3 — the forward cg limit is set by elevator effectiveness; expressing that limit as a static margin is Eq. 11.18 applied to that cg. Sadraey §11.6.3 Table: "Take-off rotation → Forward [cg limit] → Elevator effectiveness."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
x_cg,fwd from elevator control power (Eq. 11.23–11.25); SM_max,fwd = (x_np − x_cg,fwd)/C̄
```

**⚠️ Divergence from the source.** Sadraey derives the forward limit from the TAKE-OFF ROTATION case (elevator must rotate the aircraft about the main gear at 80 % of take-off speed, 6–8 deg/s² initial angular acceleration, rotation complete in 3–4 s — §11.6.3). The code derives it from a LANDING-STALL trim inversion. Those are different critical conditions and generally give different answers; Sadraey's §12.5.4 uses low-speed/most-aft-cg for the *positive* deflection limit and take-off rotation for the *negative* one.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The docstring credits gh-500 elevator authority for cg_stability_fwd_m, but that service can never return a value (notes F1) — in practice this always resolves to the 0.30·MAC stub, making sm_max_fwd ≈ 0.30 by construction.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `sm_max_fwd    = (x_NP - cg_stability_fwd_m) / MAC  (from gh-500 elevator authority)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
