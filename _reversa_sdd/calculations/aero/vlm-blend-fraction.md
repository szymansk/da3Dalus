---
name: vlm-blend-fraction
symbol: frac
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# Inserted-section blend fraction

**Definition.** Linear parameter locating an inserted cross-section between the two bounding xsecs.

**Formula — as the code writes it.**

```
a, b = 1.0 - frac, frac   /   _blend_xsec(xa, xb, i / n)
```

**Inputs.** [[vlm-panels-per-segment|Panels allotted to a wing segment]]

**Produced by.** `app/services/vlm_strip_forces.py:97` — `_blend_xsec`

**Consumed by.**

- in this graph: [[vlm-blend-airfoil|Blended section airfoil]] · [[vlm-blend-chord|Blended section chord]] · [[vlm-blend-twist|Blended section twist]] · [[vlm-blend-xyz-le|Blended section leading-edge point]]
- outside it: `app/services/vlm_strip_forces.py:_blend_xsec`

**Source.** 🟡 PARTIAL

> AeroSandbox tutorial 06, VLM point analysis ('The airfoil is blended linearly between consecutive XSecs')
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Linear parameter i/n is the implementation of the documented linear loft. Bookkeeping.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:97,135`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
