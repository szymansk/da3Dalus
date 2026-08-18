---
name: cl-alpha-per-rad
symbol: C_Lα
kind: parameter
unit: 1/rad
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/aero-spanwise
  - class/unclassified-parameter
  - source/sourced
  - flag/divergence
---

# Lift-curve slope from context

**Definition.** Lift-curve slope read out of the cached assumption computation context.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
raw_cl_alpha = ctx.get("cl_alpha_per_rad"); cl_alpha_from_ctx = float(raw_cl_alpha) if raw_cl_alpha is not None else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:643` — `_build_speed_polar`

**Consumed by.**

- in this graph: `Alpha at best glide` · `Alpha at minimum sink` · `Alpha at stall`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 (lift slope a₀, independent of Reynolds number); Sadraey §5.4.3 feature 7
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
C_lα ≈ 2π /rad (≈ 0.1 /deg); empirical: C_lα = 1.8π·(1 + 0.8·t_max/c) [1/rad]
```

**⚠️ Divergence from the source.** Code reads a fitted per-radian slope from the computation context rather than computing it — correct unit, but authority lives elsewhere.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
