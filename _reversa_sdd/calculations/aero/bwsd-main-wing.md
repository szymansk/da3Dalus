---
name: bwsd-main-wing
symbol: main_wing
kind: quantity
unit: n/a
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Main wing selection

**Definition.** The wing with the largest planform area is taken as the main wing for airfoil lookup.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
main_wing = max(asb_airplane.wings, key=lambda w: float(w.area()))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:399` — `build_wing_section_data`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Per-section airfoil name`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L240-295 (Sref is the reference area, conventionally the main wing); Scholz, Flugzeugentwurf 05_PreliminarySizing §5.6.2 (S_W)
>
> — via `avl-advisor, aircraft-design-scholz`

**The source states it as.**

```
S_ref = main-wing planform area
```

**⚠️ Divergence from the source.** Max-area selection is the correct realisation of the definition — and it CONTRADICTS section_aoa_service.py:495, which takes the first symmetric wing for the same concept. One of the two is wrong by the cited definition, and it is not this one.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:399`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
