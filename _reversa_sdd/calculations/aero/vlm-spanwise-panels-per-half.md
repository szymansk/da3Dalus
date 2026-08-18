---
name: vlm-spanwise-panels-per-half
symbol: _SPANWISE_PANELS_PER_HALF
kind: constant
unit: panels
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Spanwise panel budget per half-wing

**Definition.** Target number of spanwise panels distributed over one half-wing before the VLM solve.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `40`

**Formula — as the code writes it.**

```
_SPANWISE_PANELS_PER_HALF = 40
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:59` — `_SPANWISE_PANELS_PER_HALF`

**Consumed by.**

- in this graph: `Panels allotted to a wing segment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/vlm_strip_forces.py:_remesh_airplane` · `app/services/vlm_strip_forces.py:compute_vlm_strip_forces`

**Source.** 🔴 NO SOURCE FOUND

> AeroSandbox docs_aero_3d.md (VortexLatticeMethod: spanwise_resolution default = 10 per section); Drela & Youngren, AVL 3.40 User Primer, avl_doc.txt L1040-1082 (panel refinement study)
>
> — via `aerosandbox-expert, avl-advisor`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source prescribes 40. AVL's own refinement study is the nearest quantitative anchor and it measures the OTHER variable: with cosine spacing e is converged at Nj=8; with uniform spacing e error is +13.4% (Nj=4), +6.4% (8), +3.1% (16), +1.5% (32) — error falls only linearly. Since this code uses uniform spanwise spacing, 40/half buys roughly the accuracy 8-16 cosine panels would.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no cited source; gh-855 comment gives intent but no aerodynamic justification for 40.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:59`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
