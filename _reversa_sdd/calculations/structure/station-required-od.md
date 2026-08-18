---
name: station-required-od
symbol: required_od
kind: quantity
unit: mm
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

# Station strength-required OD

**Definition.** The minimum solid-rod diameter at the station that meets the required section modulus — the solver's sole strength input per station.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
required_od = float(sol["solved_mm"]) if sol["solved_mm"] else 0.0
```

**Inputs.**

- [[station-erf-w|Station required section modulus (plan path)]]
- [[solved-rod-diameter|Solved rod diameter]]
- [[rod-outer-fallback-1mm|Rod sizing outer-dimension floor]]  — *⤵ fallback*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:768` — `build_stations_from_geometry`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Governing required OD of a piece` · `Reinforcement outer diameter`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:303` · `cad_designer/airplane/geometry/spar_solver.py:617`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — the rod section-modulus values on that page (equal to d³/10) inverted for d; procedure step 4
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
The source gives W(d) as a table and asks the designer to verify W_available > W_required; it never solves for d.
```

**⚠️ Divergence from the source.** See `solved-rod-diameter` for the inversion's error direction. Two further issues independent of provenance: a falsy solved_mm silently becomes required_od = 0.0, indistinguishable from a genuinely zero-moment station (ADR 0020); and this is ALWAYS a rod-equivalent diameter regardless of SparPlanRequest.shape, because `shape` is not forwarded here — so the 'capped' shape, the only one the cited source gives in closed form, never reaches its own formula.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): a falsy solved_mm silently becomes 0.0 required OD — an unloaded station, indistinguishable from a genuinely zero-moment one. Also: this is ALWAYS a rod-equivalent diameter regardless of SparPlanRequest.shape, because shape is not forwarded here.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** ```required_od`` is the strength-required outer diameter from #1008 sizing at this station.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
