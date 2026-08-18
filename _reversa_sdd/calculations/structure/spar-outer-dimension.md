---
name: spar-outer-dimension
symbol: outer_mm
kind: quantity
unit: mm
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
---

# Spar outer dimension

**Definition.** The outer dimension available to the spar at the station: the airfoil profile thickness reduced by the packing factor (the remainder is skin/glue clearance). It fixes the constrained dimension for every shape.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
outer_mm = profile_thickness_mm * params.packing_factor
```

**Inputs.**

- [[profile-thickness-mm|Local airfoil profile thickness]]
- [[structure--packing-factor|Packing factor]]

**Produced by.** `app/services/spar_sizing.py:323` — `compute_spar_sizing`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Capped-spar flange (gurt) thickness` · `Capped-spar inner-height cube` · `Rectangular cross-section area` · `Solved rectangular width` · `Solved tube wall thickness` · `Tube cross-section area` · `Tube inner-diameter discriminant`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:326` · `app/services/spar_sizing.py:338` · `app/schemas/spar_sizing.py:62` · `frontend/components/workbench/SparSizingPanel.tsx:106` · `frontend/lib/sparSizingHelpers.ts:92`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 07_WingDesign §7.4 and the derived concept [[wing-box-spars]]; RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm; Lennon, The Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 13, Figs. 6-8
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
The PRINCIPLE is attributable and unanimous across all three: the spar's structural depth is set by the local airfoil depth, and the flanges must sit as far apart as the section allows. Lennon Ch. 13: the spar is "placed at or near the thickest point of the airfoil so the flanges are as far from the neutral axis as possible". Scholz §7.4 / thickness-ratio: bending stiffness ∝ (box height)³. RC-Network "Holm": Holmgurte are "positioned at the maximum distance apart (top and bottom of the airfoil)".
```

**⚠️ Divergence from the source.** The principle (outer dimension ∝ local section depth) is well sourced; the specific reduction by a multiplicative packing factor is not (see `packing-factor`). Note also the two pipelines apply it differently — spar_sizing.py:323 multiplies a chord·(t/c) ESTIMATE by 0.8, while spar_solver.py:761-763 insets the REAL lofted section by (1−packing)/2 per side. No source supports one over the other.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Independent second definition of the same concept in the plan path: the containment band (band_hi − band_lo) at spar_solver.py:762-763 applies the clearance as (1−packing)/2 on each side of the REAL section, not as a single multiplicative factor on a chord·(t/c) estimate.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `outer = chord(y) · (t/c)(y) · packing`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
