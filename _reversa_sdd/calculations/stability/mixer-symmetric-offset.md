---
name: mixer-symmetric-offset
symbol: δ_sym
kind: quantity
unit: deg
cluster: stability
user_visible: true
source_status: SOURCED
---

# Mixer symmetric offset

**Definition.** Symmetric (pitch or lift) component of a mixed control surface's deflection, after the primary mix gain.

**Formula — as the code writes it.**

```
d_sym = gp * primary_val
```

**Inputs.** [[mix-gain-primary|Primary mix gain]]

**Produced by.** `app/services/trim_enrichment_service.py:304` — `decompose_dual_role`

**Consumed by.**

- in this graph: [[mixer-left-right-deflection|Mixer left/right physical deflections]]
- outside it: `app/services/trim_enrichment_service.py:321,323,324` · `frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23 (tailless elevon mixing) — an elevon carries a symmetric (pitch) component and an antisymmetric (roll) component superposed on the same surface. Sadraey §12.4 / §12.8 (unconventional control surfaces) treats elevons and ruddervators as combined-function surfaces decomposed into their symmetric and differential parts.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
δ_surface = δ_symmetric ± δ_antisymmetric (elevon/ruddervator mixing)
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
