---
name: saoa-alpha-l0-sweep
symbol: alphas
kind: constant
unit: deg
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Alpha sweep for zero-lift angle

**Definition.** Alpha grid over which the NeuralFoil polar is evaluated to find CL = 0.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `np.linspace(-6.0, 2.0, 40)`

**Formula — as the code writes it.**

```
alphas = np.linspace(-6.0, 2.0, 40)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:179` — `_compute_alpha_l0_per_section`

**Consumed by.**

- in this graph: `Section zero-lift angle`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Anderson, Fundamentals of Aerodynamics 6e, §4.8 (alpha_L=0 = -(1/pi) * integral of (dz/dx)(cos(theta_0) - 1) d(theta_0) — set purely by camber, with no bound)
>
> — via `aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Real and two-sided. alpha_L0 is unbounded by camber, so a fixed [-6 deg, +2 deg] window is not safe at either end. A high-camber low-Re RC section (Selig S1223 class, alpha_L0 near -8 deg) falls BELOW the window; a reflexed flying-wing section can sit ABOVE +2 deg. In both cases np.interp clamps to an endpoint and returns a wrong alpha_L0 with no warning.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** High-camber sections are the norm, not the exception, for slow 0.5-15 kg aircraft, so the failing case is the target case rather than an edge case.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The window is capped at +2°, so a strongly reflexed or negatively cambered section whose alpha_L0 exceeds +2° cannot be found and silently extrapolates.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:179`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
