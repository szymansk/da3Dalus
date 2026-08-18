---
name: de-da-factor
symbol: (1 - dε/dα)
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Downwash factor (1 − de/dalpha)

**Definition.** Fraction of free-stream angle-of-attack change seen by the horizontal tail after wing downwash.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.6`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:75` — `_DE_DA_FACTOR`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Tail efficiency factor` · `SM sensitivity to horizontal tail area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:122 (_alpha_vh)` · `app/services/sm_sizing_service.py:162 (_dsm_dsh)`

**Source.** 🟡 PARTIAL

> The downwash-gradient method is standard and citable: Sadraey (Wiley 2013) §6.7.4 — ε = ε_o + (∂ε/∂α)·α_w with ε_o = 2C_Lw/(π·AR) and ∂ε/∂α = 2C_Lα_w/(π·AR); Sadraey states "Typical numbers are ε_o ≈ 1 deg and ∂ε/∂α ≈ 0.3 rad/rad." Anderson, "Fundamentals of Aerodynamics" 6e Ch. 5 §5.1 gives the underlying downwash/induced-angle physics. The code's own citation, Roskam Vol I §8.1, could not be verified from any consulted vault.
>
> — via `aircraft-design-scholz + aerodynamics-expert + rc-aircraft-designer`

**The source states it as.**

```
∂ε/∂α = 2·C_Lα_w / (π·AR)   ⇒   (1 − ∂ε/∂α) computed per aircraft, not fixed
```

**⚠️ Divergence from the source.** Two divergences. (a) Value: Sadraey's typical ∂ε/∂α ≈ 0.3 gives (1 − dε/dα) ≈ 0.7, not 0.6. (b) Form: Sadraey makes the gradient a function of wing aspect ratio and lift-curve slope; the code hardcodes it as configuration-independent. Since ∂ε/∂α ∝ 1/AR, a low-AR RC wing has a materially larger gradient (smaller factor) and a high-AR glider a smaller one — the constant is wrong in opposite directions at the two ends of this app's own aircraft classes.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The code attributes 0.6 to Roskam Vol I §8.1 — transport/GA-category literature. No RC/UAV-scale (0.5–15 kg) validation is recorded, and the AR-dependence that would carry the value across scales has been discarded (ADR 0023). Lennon Ch. 8 does give an RC-scale downwash method (NACA Report No. 648 wake-centreline charts), which the code does not use.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Roskam Vol I is transport/GA-category literature; no RC/UAV-scale (0.5–15 kg) validation is recorded (ADR 0023). It is also treated as configuration-independent — a low-AR RC wing has a materially different downwash gradient.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Roskam Vol I §8.1: downwash factor (1 - dε/dα) for conventional tail
_DE_DA_FACTOR = 0.6  # (1 - dε/dα), typical for conventional aft tail`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
