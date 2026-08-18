---
name: sui-nu
symbol: ν
kind: constant
unit: m²/s
cluster: aero-polars
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/aero-polars
  - class/physical-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Kinematic viscosity for per-lens Re

**Definition.** Kinematic viscosity used only for the per-lens (gh-838) Reynolds numbers.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: kinematic viscosity of air.*

**Value.** `1.46e-5`

**Formula — as the code writes it.**

```
_NU = 1.46e-5  # kinematic viscosity m²/s at 15°C
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/suitability_service.py:377` — `search_suitability (inner)`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Per-lens Reynolds number`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_per_lens_re:383`

**Source.** 🟢 SOURCED

> ICAO Standard Atmosphere / ISO 2533:1975, sea level: ν = μ/ρ = 1.7894e-5/1.225 = 1.4607e-5 m²/s
>
> — via `aerodynamics-expert`

**The source states it as.**

```
ν_ISA,SL = 1.4607e-5 m²/s
```

**⚠️ Divergence from the source.** 1.46e-5 is the correct ISA SL kinematic viscosity — this constant is right and its siblings are wrong, not the other way round. _RHO/_MU in the same function give ν = 1.478e-5, so slider Re and per-lens Re at identical speed and chord differ by 1.2%, enough to bracket different grid rows (ADR 0022). Fix by deriving ν from the ISA μ, not by changing _NU.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Contradicts _RHO/_MU in the same function: μ/ρ = 1.81e-5/1.225 = 1.478e-5, so root Re and per-lens Re at the SAME speed differ by ~1.2% — two producers of Reynolds number with different viscosities.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `_NU = 1.46e-5  # kinematic viscosity m²/s at 15°C`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
