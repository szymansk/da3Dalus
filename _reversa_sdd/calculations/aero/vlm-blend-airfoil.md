---
name: vlm-blend-airfoil
symbol: airfoil
kind: quantity
unit: n/a
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Blended section airfoil

**Definition.** Airfoil of an inserted section, blended between the bounding airfoils.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
xa.airfoil.blend_with_another_airfoil(airfoil=xb.airfoil, blend_fraction=b)
```

**Inputs.**

- [[vlm-blend-fraction|Inserted-section blend fraction]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:106` — `_blend_xsec`

**Consumed by.**

- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🟢 SOURCED

> AeroSandbox tutorial 06, VLM point analysis: 'The airfoil is blended linearly between consecutive XSecs'
>
> — via `aerosandbox-expert`

**The source states it as.**

```
airfoil(eta) = (1-eta)*airfoil_inboard + eta*airfoil_outboard
```

**⚠️ Divergence from the source.** Formula matches the documented ASB convention. The silent except that keeps the inboard airfoil on failure is the undeclared part, not the formula.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: a blend exception silently keeps the inboard airfoil (line 107-108), no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:106`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
