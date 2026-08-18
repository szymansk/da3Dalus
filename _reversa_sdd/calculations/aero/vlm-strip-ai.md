---
name: vlm-strip-ai
symbol: ai
kind: quantity
unit: deg
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
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Strip induced angle

**Definition.** Local induced angle of attack from the drag/lift ratio of the strip.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ai_deg = math.degrees(math.atan2(drag, lift))
```

**Inputs.**

- [[vlm-strip-drag|Strip drag force]]
- [[vlm-strip-lift|Strip lift force]]

**Produced by.** `app/services/vlm_strip_forces.py:276` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.ai` · `frontend/components/workbench/AnalysisViewerPanel.tsx:501`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (downwash tilts the local lift vector rearward by alpha_i, producing induced drag)
>
> — via `aerodynamics-expert, avl-advisor`

**The source states it as.**

```
D_i' = L_eff' * sin(alpha_i), L' = L_eff' * cos(alpha_i)  =>  tan(alpha_i) = D_i'/L'
```

**⚠️ Divergence from the source.** Two-part. (1) vs Anderson: the textbook states the small-angle form D_i' = L' * alpha_i; atan2(drag, lift) is the exact form of the same relation, so this is a refinement, not an error. (2) vs AVL, which is the real problem: AVL's 'ai' column is DWWAKE(J), documented in Avl/src/AVL.INC:314 as 'downwash in Trefftz plane' — a FAR-FIELD quantity. The VLM path fills the identical API field with a NEAR-FIELD force ratio. Near-field strip drag in a VLM is contaminated by leading-edge suction resolution, so the two producers of StripForceEntry.ai are not the same physical quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the induced angle: section_aoa_service computes induced_angle_deg from a different method (LiftingLine + thin-airfoil cl) at a different resolution (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:276`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
