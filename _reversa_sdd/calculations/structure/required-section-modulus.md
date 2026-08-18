---
name: required-section-modulus
symbol: erf_W
kind: quantity
unit: mm³
cluster: structure
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Required section modulus

**Definition.** The section modulus the spar cross-section must provide at a station to keep bending stress at or below the allowable. The 1000.0 converts N·m to N·mm so the result is mm³ against σ in N/mm².

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return m_design_Nm * 1000.0 / sigma_allow_mpa
```

**Inputs.**

- [[design-bending-moment|Design bending moment]]  — *⊣ limit*
- [[sigma-allow-mpa|Allowable bending stress (sizing path)]]
- [[mm-per-metre-factor|Metre-to-millimetre conversion factor]]  — *× unit*

**Produced by.** `app/services/spar_sizing.py:88` — `required_section_modulus`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Capped-spar inner-height cube` · `Solved rectangular width` · `Solved rod diameter` · `Station required section modulus (plan path)` · `Tube inner-diameter discriminant`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:318` · `cad_designer/airplane/geometry/spar_solver.py:765` · `app/schemas/spar_sizing.py:79` · `frontend/hooks/useSparSizing.ts:24` · `frontend/components/workbench/SparSizingPanel.tsx:107` · `frontend/lib/sparSizingHelpers.ts:91`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — main-spar design procedure, step 2 of 5
>
> — via `direct verification of the kirch source named in the code (RC model-building, scale-appropriate)`

**The source states it as.**

```
The source's procedure is: (1) required bending moment M = P × l (load × moment arm); (2) required section modulus W_req = M / σ_allowable; (3) available section modulus from geometry; (4) verify W_available > W_required; (5) taper flange dimensions linearly outboard from root.
```

**⚠️ Divergence from the source.** The code (app/services/spar_sizing.py:88, `return m_design_Nm * 1000.0 / sigma_allow_mpa`) adds the ×1000 N·m→N·mm factor that the source does not need because it works in kg/cm² and cm throughout. The relation itself is identical. Note the code implements steps 1-2 and 4 of the source procedure but NOT step 5 (linear flange taper outboard) — it re-solves the free dimension independently at every station instead.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `erf_W = M_design [N·m] × 1000 [mm/m] / σ_allow [N/mm²]`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
