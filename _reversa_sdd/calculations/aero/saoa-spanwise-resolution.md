---
name: saoa-spanwise-resolution
symbol: _SPANWISE_RESOLUTION
kind: constant
unit: panels
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# LiftingLine spanwise resolution

**Definition.** Panels per half-span used by the section-AoA LiftingLine run.

**Value.** `8`

**Formula — as the code writes it.**

```
_SPANWISE_RESOLUTION = 8  # panels per half-span — fast, physically sane
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:63` — `_SPANWISE_RESOLUTION`

**Consumed by.**

- outside it: `app/services/section_aoa_service.py:compute_section_aoa` · `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:115 (via compute_section_aoa)` · `app/services/assumption_compute_service.py:149`

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md (LiftingLine default spanwise_resolution = 4; NonlinearLiftingLine default = 8); Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013) §5.14, Step 1
>
> — via `aerosandbox-expert, aircraft-design-scholz`

**The source states it as.**

```
Sadraey: divide the semispan into N segments; 'smaller segments near the tip give better accuracy'
```

**⚠️ Divergence from the source.** 8 sits between the two ASB defaults, so the value is plausible, but nothing prescribes it. Two documented concerns: Sadraey asks for tip clustering (ASB LiftingLine defaults to np.cosspace, which the code leaves alone — good), and 8 half-span panels silently becomes the turbulator optimiser's section count, i.e. a solver mesh parameter doubles as a design-output resolution.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number: 8 half-span panels also fixes the turbulator optimiser's section count, yet the comment justifies it only as 'fast, physically sane'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:63`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
