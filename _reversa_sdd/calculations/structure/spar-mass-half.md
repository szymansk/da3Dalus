---
name: spar-mass-half
symbol: m_spar,half
kind: quantity
unit: kg
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Half-span spar mass

**Definition.** Estimated mass of the spar over one half-span, by trapezoidal integration of the per-station cross-section area against spanwise position and material density.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
dy = abs(ys_m[i] - ys_m[i + 1])  # segment length (m)
avg_area_mm2 = (areas_mm2[i] + areas_mm2[i + 1]) / 2.0
avg_area_m2 = avg_area_mm2 * 1e-6  # mm² → m²
volume_m3 = avg_area_m2 * dy
total_mass += density_kg_m3 * volume_m3
```

**Inputs.**

- [[tube-cross-section-area|Tube cross-section area]]
- [[rod-cross-section-area|Rod cross-section area]]
- [[rectangular-cross-section-area|Rectangular cross-section area]]
- [[capped-cross-section-area|Capped-spar cross-section area]]
- [[material-density|Material density]]
- [[mm2-to-m2-factor|Square-millimetre to square-metre factor]]  — *ε tolerance*

**Produced by.** `app/services/spar_sizing.py:250` — `spar_mass_half_kg`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Full-span spar mass`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:360` · `app/services/spar_sizing.py:382` · `app/schemas/spar_sizing.py:136` · `frontend/hooks/useSparSizing.ts:43` · `frontend/lib/sparSizingHelpers.ts:104`

**Source.** 🟡 PARTIAL

> No source prescribes trapezoidal integration of spar cross-section area. Attributable ALTERNATIVE: Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1, Eq. (10.3) — wing weight from planform geometry and material density. Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm, procedure step 5 ("taper flange dimensions linearly outboard from root") implies a spanwise-varying section but gives no mass integral.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey Eq. (10.3): W_W = S_W · MAC · (t/C)_max · ρ_mat · K_ρ · (AR · n_ult / cos Λ_0.25)^0.6 · λ^0.04 · g, with K_ρ from Table 10.8 (Remotely controlled model: 0.001-0.0015).
```

**⚠️ Divergence from the source.** Sadraey's method is an empirical regression for the WHOLE wing (skin + spars + ribs + stringers), calibrated by K_ρ; the code integrates ρ·A(y) for the SPAR ALONE. They are not substitutes and must not be cross-validated against each other. The trapezoidal integral itself is a numerical choice with no cited basis.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey Eq. (10.3) and its RC K_ρ row are transport-through-RC regression fits, and per the project's own settled record (BR-W16/BR-W17, gh-1079) the RC row of Table 10.9 that feeds n_ult in this equation is a regression coefficient co-fitted with K_ρ — it is not a design load and must not be transferred into spar sizing.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared fallback: infeasible stations contribute area 0.0 (spar_sizing.py:357), so a plan with infeasible stations silently under-reports mass instead of refusing to report it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
