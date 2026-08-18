---
name: mixer-left-right-deflection
symbol: δ_L, δ_R
kind: quantity
unit: deg
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mixer left/right physical deflections

**Definition.** Physical left and right surface angles obtained by superposing the symmetric offset onto the differentially scaled antisymmetric component.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
right = d_anti
left = -d_anti
if right < 0:
    right *= diff
if left < 0:
    left *= diff
...
deflection_left=round(d_sym + left, 3),
deflection_right=round(d_sym + right, 3),
```

**Inputs.**

- [[mixer-symmetric-offset|Mixer symmetric offset]]
- [[mixer-antisymmetric|Mixer antisymmetric component]]
- [[differential-ratio|Aileron differential ratio]]

**Produced by.** `app/services/trim_enrichment_service.py:313` — `decompose_dual_role`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:323,324` · `frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23 (elevon mixing: physical left/right angles are the superposition of pitch and roll commands) and Ch. 10 (differential linkage geometry: "Differential is easily introduced when servos actuate the ailerons via moving horns … arranged to produce more up-travel than down-travel").
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
δ_L = δ_sym − δ_anti·k_L ,  δ_R = δ_sym + δ_anti·k_R, with the up-going side scaled by the differential ratio (Lennon Ch. 10)
```

**⚠️ Divergence from the source.** The superposition matches Lennon. What is missing is the check the sources demand: Sadraey §12.5.5 steps 19–21 requires the RESULTING physical deflection to be verified against the surface limit and against tail stall. Here the reserve/authority warnings are computed from the pre-decomposition control variables (trim_enrichment_service.py:412), so a mixed surface whose combined left angle exceeds its hinge limit produces no warning at all.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** These physical angles are never checked against the mechanical deflection limits — the reserve/authority warnings are computed from the pre-decomposition control variables (line 412), so a mixed surface whose combined left angle exceeds its hinge limit produces no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Differential is taken about the symmetric/neutral reference (as a real
# differential linkage is): scale the side whose ANTISYMMETRIC excursion is
# up-relative-to-symmetric (negative), i.e. the larger-throw side.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
