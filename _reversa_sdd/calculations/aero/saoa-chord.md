---
name: saoa-chord
symbol: chord_m
kind: quantity
unit: m
cluster: aero-strips
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/liftingline
---

# Panel chord

**Definition.** Local chord of each LiftingLine panel.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
chord_arr = np.array(ll.chords).flatten()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:273` — `compute_section_aoa`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Local section Reynolds number` · `Raw trapezoidal section area` · `Section lift coefficient (Kutta-Joukowski)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaPoint.chord_m` · `app/services/turbulator_optimizer_service.py:build_wing_section_data`

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md, LiftingLine (per-section chord used for local Re and sectional aero)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** API read-through, no formula.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:273`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
