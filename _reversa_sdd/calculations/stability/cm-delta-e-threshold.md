---
name: cm-delta-e-threshold
symbol: —
kind: constant
unit: 1/rad
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Elevator authority conditioning threshold

**Definition.** Magnitude of Cm_δe below which elevator authority is deemed critically low and the forward CG envelope is collapsed onto x_NP.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.005`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:83` — `_CM_DELTA_E_THRESHOLD`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/elevator_authority_service.py:260,266`

**Source.** 🟡 PARTIAL

> The quantity is well sourced: Sadraey (Wiley 2013) §12.5.2 Eq. 12.51, C_mδE = −C_Lα_h·η_h·V_H·(b_E/b_h)·τ_e, with "Typical value: C_mδE = −0.2 to −4 1/rad" and "For transports the design target is typically C_mδE < −2 1/rad". The specific cutoff 0.005 1/rad is not attributable — the code's reference, 'Amendment S1', is an internal spec note, not a literature source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mδE = −C_Lα_h · η_h · V̄_H · (b_E/b_h) · τ_e   (Sadraey Eq. 12.51); typical magnitude 0.2–4 1/rad
```

**⚠️ Divergence from the source.** 0.005 1/rad is 40× below the bottom of Sadraey's typical range (0.2) and 400× below the transport target. As a 'critically low' guard it will essentially never fire on a real elevator — anything above 0.005 passes, including values Sadraey would call unusable. Sadraey's own guard is different in kind: τ_e > 1 or required δ_E above the deflection limit means 'no elevator can satisfy the requirement, redesign upstream' (§12.5.5 steps 13, 19).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's C_mδE band (−0.2 to −4 1/rad, transport target < −2) is transport/GA-category. No RC/UAV-scale validation of either the band or the 0.005 cutoff is recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** 'Amendment S1' is an internal spec reference, not an external source — no aerodynamic citation, and no RC/UAV-scale validation (ADR 0023). Unreachable in practice (notes F1).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Conditioning guard threshold (Amendment S1): below this Cm_δe the elevator
#: authority is critically low and the forward CG envelope vanishes.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
