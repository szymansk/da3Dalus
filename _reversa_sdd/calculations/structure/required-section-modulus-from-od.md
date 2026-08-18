---
name: required-section-modulus-from-od
symbol: W
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Section modulus provided by a solid rod

**Definition.** The section modulus a solid rod of the given diameter provides. Used to invert a strength-required OD back into a required W, keeping the solver decoupled from the original moment while staying load-consistent.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return od**3 / 10.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:521` — `required_section_modulus_from_od`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Strength bore from tube sizing`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:507` · `cad_designer/airplane/geometry/spar_solver.py:626`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — the rod values tabulated on that page equal d³/10 (verified: d=3→2.7, d=5→12.5, d=6→21.6; the exact π·d³/32 gives 2.65, 12.27, 21.21)
>
> — via `direct verification of the kirch source named in the code`

**The source states it as.**

```
The source gives a table of round-rod section moduli, not this closed form. See `section-modulus-rod` for the full arithmetic check.
```

**⚠️ Divergence from the source.** This is the FOURTH independent implementation of one relation (also app/services/spar_sizing.py:62, app/services/spar_plan_service.py:218, and the rod branch of _w_stock at spar_plan_service.py:74). The source states it once, as a table.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two further independent producers of the identical formula: app/services/spar_sizing.py:62 (section_modulus_rod) and app/services/spar_plan_service.py:218 (_erf_w_for_piece), plus the rod branch of _w_stock at spar_plan_service.py:74. Four copies of one relation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#1008 sizes the strength OD as the minimum solid-rod diameter, so its section modulus W = d³/10 is exactly the required W. Inverting keeps the solver decoupled from the original moment while staying load-consistent.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
