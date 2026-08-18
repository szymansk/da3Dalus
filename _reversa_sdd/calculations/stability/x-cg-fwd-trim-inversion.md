---
name: x-cg-fwd-trim-inversion
symbol: x_cg_fwd
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: PARTIAL
---

# Forward CG limit (trim inversion)

**Definition.** Furthest-forward CG at which the aircraft can still be trimmed at landing stall with full TE-UP elevator.

**Formula — as the code writes it.**

```
return x_np_m - net_pitch_up * c_ref_m / cl_max_landing
```

**Inputs.** [[net-pitch-up|Net nose-up moment coefficient]] · [[cl-max-landing|Landing CL_max]]

**Produced by.** `app/services/elevator_authority_service.py:237` — `_trim_inversion`

**Consumed by.**

- in this graph: [[sm-max-fwd|Maximum forward-CG static margin]]
- outside it: `app/services/elevator_authority_service.py:783,797,819,828 (ASB path)` · `app/services/elevator_authority_service.py:1124,1135,1156,1163 (AVL path)` · `app/services/assumption_compute_service.py:484-485 (would overwrite cg_stability_fwd_m)`

**Source.** 🟡 PARTIAL

> The forward CG limit set by elevator authority is firmly sourced: Sadraey (Wiley 2013) §11.6.3 ("The forward cg limit is therefore set by elevator effectiveness during rotation") with Eqs. 11.23–11.25, and §12.5.5 steps 17–19. The specific closed form x_cg_fwd = x_np − (C_m,ac + C_mδe·δe_max + ΔC_m,flap)·c_ref/CL_max,landing is NOT found in any consulted source. The code's citation "Anderson §7.7" is a misattribution: Anderson, "Fundamentals of Aerodynamics" 6e Chapter 7 is "Compressible Flow: Some Preliminary Aspects" — it contains no stability, trim or CG material. The relevant Anderson book is "Introduction to Flight" (stability-and-control chapter: contribution of the tail, neutral point, static margin, elevator angle to trim).
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
Sadraey Eq. 11.23: δ_E = −(C_Lα·C_mo + C_mα·C_L)/(C_Lα·C_mδE − C_L_δE·C_mα), with C_L_δE = (S_h/S)(dC_Lt/dδ_E) and C_mδE = −V̄_H·(dC_Lt/dδ_E); the forward cg is the one at which the required δ_E reaches δ_E,max.
```

**⚠️ Divergence from the source.** Three substantive differences from Sadraey. (a) Critical condition: Sadraey sizes the forward limit from TAKE-OFF ROTATION about the main gear (§11.6.3: nose-lift at 80 % of take-off speed, 6–8 deg/s² initial angular acceleration, 3–4 s to complete), not from landing-stall trim. (b) Structure: Sadraey solves a 2×2 system in (α, δ_E) (Eq. 12.86) and finds the cg at which δ_E saturates; the code inverts a single moment equation algebraically. (c) The code's denominator CL_max,landing implicitly assumes lift equals weight at the stall point with the whole lift acting at the neutral point — an assumption no consulted source states.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** UNREACHABLE in production — every call path raises before reaching it because the x_np/mac design-assumption rows it depends on are never written (notes F1). The 0.30·MAC stub always wins.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing
(Anderson §7.7, Amendment B1)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
