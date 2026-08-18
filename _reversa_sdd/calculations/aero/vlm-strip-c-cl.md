---
name: vlm-strip-c-cl
symbol: c_cl
kind: quantity
unit: m
cluster: aero-strips
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/vlm
---

# Chord × cl product

**Definition.** Local chord times local lift coefficient — the spanwise load ordinate.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"c_cl": chord * cl
```

**Inputs.**

- [[vlm-strip-chord|Local strip chord]]
- [[vlm-strip-cl|Local strip lift coefficient]]

**Produced by.** `app/services/vlm_strip_forces.py:287` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.c_cl` · `frontend/components/workbench/AnalysisViewerPanel.tsx:500`

**Source.** 🟢 SOURCED

> AVL 3.40 source, Avl/src/aero.f:358 ('accumulate strip spanloading = c*CN', CNC(J) = sum of CR*(ENSY*DCFY + ENSZ*DCFZ)); Anderson, Fundamentals of Aerodynamics 6e, §5.3 (c*cl = 2*Gamma/V_inf, the spanload ordinate)
>
> — via `avl-advisor, aerodynamics-expert`

**The source states it as.**

```
AVL c_cl = chord * c_n (strip NORMAL-force coefficient, dihedral-normal direction)
```

**⚠️ Divergence from the source.** AVL multiplies the chord by the strip normal-force coefficient; the app multiplies it by the strip LIFT coefficient. They agree to O(alpha^2) on a planar wing and diverge by cos(dihedral) and by the axial-force term on a V-tail or high-dihedral surface.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:287`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
