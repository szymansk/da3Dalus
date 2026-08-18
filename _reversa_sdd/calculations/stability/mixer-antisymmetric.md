---
name: mixer-antisymmetric
symbol: δ_anti
kind: quantity
unit: deg
cluster: stability
user_visible: true
source_status: SOURCED
---

# Mixer antisymmetric component

**Definition.** Antisymmetric (roll or yaw) component of a mixed control surface's deflection, after the secondary mix gain.

**Formula — as the code writes it.**

```
d_anti = gs * secondary_val
```

**Inputs.** [[mix-gain-secondary|Secondary mix gain]]

**Produced by.** `app/services/trim_enrichment_service.py:305` — `decompose_dual_role`

**Consumed by.**

- in this graph: [[mixer-left-right-deflection|Mixer left/right physical deflections]]
- outside it: `app/services/trim_enrichment_service.py:313,314,322` · `frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx`

**Source.** 🟢 SOURCED

> Lennon Ch. 23 (tailless elevon mixing); Sadraey §12.8 (unconventional control surfaces — elevon, ruddervator, taileron decomposition). For a V-tail specifically, Sadraey §6.7 notes the pitch/yaw split via differential deflection of the two panels.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
δ_anti = the differential (roll or yaw) component of the mixed command
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
