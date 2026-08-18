---
name: station-erf-w
symbol: erf_W
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Station required section modulus (plan path)

**Definition.** Required section modulus at a solver station, from the station design moment and the allowable stress.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
erf_w = required_section_modulus(m_design, sigma_allow_mpa)
```

**Inputs.**

- [[station-design-moment|Station design moment (plan path)]]  — *⊣ limit*
- [[resolved-sigma-allow-plan|Allowable bending stress (plan path)]]
- [[required-section-modulus|Required section modulus]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:765` — `build_stations_from_geometry`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Station strength-required OD`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:767`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — main-spar design procedure, step 2
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
W_req = M / σ_allowable.
```

**⚠️ Divergence from the source.** Matches the source relation (it calls the shared required_section_modulus). Independent of provenance: this real value is never surfaced — the plan response carries no erf_W — and app/services/spar_plan_service.py:218 later RECONSTRUCTS an approximation of it from the piece OD through the lossy d³/10 relation, an avoidable round-trip the source's own procedure (carry M forward, compare W_available > W_required) does not require.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Not surfaced anywhere: the plan response carries no erf_W. Downstream, spar_plan_service._erf_w_for_piece:218 RECONSTRUCTS an approximation of this number from the piece OD instead of the real value being carried through — an avoidable round-trip through a lossy relation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
