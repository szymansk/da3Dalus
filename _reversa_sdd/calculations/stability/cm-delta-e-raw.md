---
name: cm-delta-e-raw
symbol: Cm_δe
kind: quantity
unit: 1/rad
cluster: stability
user_visible: true
source_status: SOURCED
---

# Elevator authority (finite difference)

**Definition.** Sensitivity of pitching moment to elevator deflection, from a two-point finite difference with TE-UP deflection.

**Formula — as the code writes it.**

```
cm_delta_e_raw = (cm_deflected - cm_baseline) / delta_e_max_rad
```

**Inputs.** [[cm-baseline|Baseline pitching moment (zero deflection)]] · [[delta-e-max-rad|Maximum elevator deflection (radians)]] · [[delta-e-neg-deg|TE-UP deflection command]]

**Produced by.** `app/services/elevator_authority_service.py:709` — `_compute_forward_cg_limit_asb`

**Consumed by.**

- in this graph: [[cm-delta-e|Elevator authority (sign-enforced)]]
- outside it: `app/services/elevator_authority_service.py:714,725` · `app/services/elevator_authority_service.py:1060,1062,1071 (AVL twin)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.2 Eq. 12.51: C_mδE = ∂C_m/∂δ_E = −C_Lα_h·η_h·V_H·(b_E/b_h)·τ_e, "Typical value: C_mδE = −0.2 to −4 1/rad". A two-point finite difference is the numerical form of that partial derivative.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mδE = −C_Lα_h · η_h · V̄_H · (b_E/b_h) · τ_e   (Sadraey Eq. 12.51)
```

**⚠️ Divergence from the source.** Sadraey computes C_mδE analytically from tail geometry (lift-curve slope, dynamic-pressure ratio, tail volume, elevator span ratio, and τ_e from the C_E/C_h chart, Fig. 12.12); the code takes a one-sided finite difference at full deflection instead of a small perturbation, so it returns a secant slope over 25°, not a derivative at zero — and at 25° the elevator is at its separation limit (§12.5.5 step 4), exactly where linearity is worst. The code's own comment says the divisor is negative while delta_e_max_rad is positive by construction (line 123).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's typical band (−0.2 to −4 1/rad) is transport/GA. No RC/UAV-scale reference band is recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The comment says the divisor is negative but delta_e_max_rad is always positive by construction (line 123), so the sign convention is carried entirely by the abs() at line 725 — the stated derivation and the code disagree.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# δe_rad is NEGATIVE (TE-UP), so Cm_δe = ΔCm / δe_rad
# We want Cm_δe per unit negative-deflection rad:
# Cm_delta_e = (Cm_deflected - Cm_baseline) / abs(delta_e_neg_deg * π/180)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
