---
name: roskam-flap-cl-bonus
symbol: ΔCL_max,flap
kind: constant
unit: – (dimensionless)
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

# Flap CL_max increment

**Definition.** Lift-coefficient increment added to the clean CL_max to estimate the landing CL_max when no flap sweep is run.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.5`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:90` — `_ROSKAM_FLAP_CL_BONUS`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Landing CL_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:361,671,1025`

**Source.** 🟡 PARTIAL

> The method is well sourced but not the constant. Scholz HAW Hamburg, 08_HighLift §8.2 (DATCOM 1978): Δc_L,max,f = k₁·k₂·k₃·(Δc_L,max)_base with base increments 0.3–0.6 for slotted flaps at reference deflection, then scaled to the wing by ΔC_L,max,f = Δc_L,max,f·(S_W,f/S_W)·K_Λ, giving ΔC_L,max,f ≈ 0.27–0.36 for large transports. Sadraey §5.17 worked example: split flap ΔC_L = 0.45 at 30°; §5.12.2: split flap Δc_l ≈ 0.7–0.9 at 60° (airfoil level). The code's cited source 'Roskam §4.7' could not be verified in any consulted vault.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΔC_L,max,f = k₁·k₂·k₃·(Δc_L,max)_base · (S_W,f/S_W) · K_Λ   (Scholz 08_HighLift §8.2)
```

**⚠️ Divergence from the source.** Every consulted source makes the increment a function of flap type, chord ratio (k₁), deflection angle (k₂), kinematics (k₃), flapped span fraction (S_W,f/S_W) and sweep (K_Λ). The code applies a single +0.5 regardless of all six. The wing-level value the sources actually produce for a transport is 0.27–0.36 — i.e. +0.5 is roughly 40–85 % high even before any of the corrections are applied. It is closer to the *airfoil-level* base increment (0.3–0.6), suggesting the airfoil→wing scaling step has been skipped.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Roskam §4.7 (as cited in the code) and the DATCOM/Scholz method are transport/GA-category. The +0.5 is applied unmodified to 0.5–15 kg RC/UAV aircraft with typically small partial-span plain flaps — the configuration for which the sources give the SMALLEST increments (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Roskam §4.7 is transport/GA-category; +0.5 is quoted for full-span Fowler-class systems and applied here regardless of flap type, span fraction or deflection, at RC/UAV scale (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Roskam §4.7 flap CL increment: CL_max_landing ≈ CL_max_clean + 0.5`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
