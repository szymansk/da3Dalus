---
name: i-ldmax-force
kind: quantity
unit: index
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Sweet-spot index

**Definition.** Alpha index of maximum force-based L/D, annotated as 'Sweet Spot'.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i_ldmax = int(np.nanargmax(ld_curve))
```

**Inputs.**

- [[ld-ratio-force|Glide ratio from forces]]

**Produced by.** `app/services/analysis_service.py:1159` — `_plot_glide_ratio`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `alpha-sweep PNG panel 4 annotation`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 (max L/D condition)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
d(C_L/C_D)/dC_L = 0 ⇒ C_D,0 = C_L²/(π e AR)
```

**⚠️ Divergence from the source.** Discrete argmax; must coincide with i-best-glide/max-ld-point (see ld-ratio-force).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
