---
name: vlm-strip-cd
symbol: cd
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
---

# Local strip drag coefficient

**Definition.** Strip (induced) drag non-dimensionalised by dynamic pressure and strip area.

**Formula — as the code writes it.**

```
cd = drag / denom if denom > 0 else 0.0
```

**Inputs.** [[vlm-strip-drag|Strip drag force]] · [[vlm-dynamic-pressure|Freestream dynamic pressure]] · [[vlm-strip-area|Strip area]]

**Produced by.** `app/services/vlm_strip_forces.py:272` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.cd` · `frontend/hooks/useStripForces.ts (typed, not plotted)`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (CD = cd + CD,i; VLM yields CD,i only)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
cd_i = D_i,strip / (q_inf * S_strip)
```

**⚠️ Divergence from the source.** Correctly labelled induced-only in the definition but the API field name 'cd' is the same one the AVL path fills with cd (induced) alongside cdv (viscous) — the two paths agree on the split, so this is naming risk rather than a formula error.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Reaches the API but no UI or backend consumer reads it; the Trefftz chart plots only cl/c_cl/cl_norm/ai.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:272`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
