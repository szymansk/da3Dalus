---
name: tos-re-rep
symbol: re_rep
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Representative Reynolds number (whole scope)

**Definition.** Area-weighted mean Reynolds number used for the single whole-wing trip optimisation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
re_rep = sum(s.re_local * s.section_area_m2 for s in sections) / total_area if total_area > 0 else sections[len(sections) // 2].re_local
```

**Inputs.**

- [[bwsd-re-local|Local section Reynolds number]]  — *⊣ limit*
- [[bwsd-section-area-normalised|Normalised section area]]

**Produced by.** `app/services/turbulator_optimizer_service.py:541` — `run_turbulator_optimizer`

**Consumed by.**

- in this graph: `Whole-wing optimal trip position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design (Wiley 2013) §5.14 (spanwise segments each carry their own local aerodynamic properties; the theory is applied per segment, not at a single representative station)
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** No source endorses collapsing a spanwise Re distribution to one number for a trip optimisation. Area weighting biases toward the root, where the chord and thus Re are highest — the OPPOSITE of where low-Re bubble trouble (and hence turbulator benefit) is worst. The docstring at line 476 also claims 'CL-weighted mean Re' while the code area-weights.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The function docstring (line 476) says 'single xtr for all sections at the CL-weighted mean Re' but the code computes an AREA-weighted Re.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:540-545`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
