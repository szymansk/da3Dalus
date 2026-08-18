---
name: saoa-a0
symbol: _A0_RAD
kind: constant
unit: 1/rad
cluster: aero-strips
user_visible: false
source_status: SOURCED
---

# Thin-airfoil lift-curve slope

**Definition.** 2π per radian section lift-curve slope used to invert cl into an effective AoA.

**Value.** `2.0 * math.pi`

**Formula — as the code writes it.**

```
_A0_RAD = 2.0 * math.pi  # thin-airfoil section lift-curve slope [/rad]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:294` — `compute_section_aoa`

**Consumed by.**

- in this graph: [[saoa-alpha-eff|Effective angle of attack]]

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.7 (thin airfoil theory: c_l = 2*pi*alpha, hence a_0 = dc_l/dalpha = 2*pi per radian) and §5.3 (c_l = 2*pi*(alpha_eff - alpha_L=0) used as the LLT closure)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
a_0 = 2*pi rad^-1
```

**⚠️ Divergence from the source.** Correct as thin-airfoil theory, but inconsistent within the function: alpha_L0 is taken from NeuralFoil (real viscous section data) while the slope is taken from inviscid thin-airfoil theory. NeuralFoil is already loaded and could supply the real dc_l/dalpha at the same (Re, section).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Thin-airfoil 2*pi (0.1097 /deg) is a HIGH-Re limit. At RC/UAV chord Reynolds numbers of 5e4-2e5 real section lift-curve slopes are typically 0.08-0.10 /deg because of the laminar separation bubble. Using a slope that is up to ~20% too steep makes alpha_eff = c_l/a_0 up to ~20% too SMALL, which propagates directly into induced_angle_deg = alpha_geom - alpha_eff, inflating the reported downwash.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `app/services/section_aoa_service.py:294`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
