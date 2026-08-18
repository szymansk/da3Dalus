---
name: alpha-0-deg
symbol: α_0
kind: parameter
unit: deg
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-spanwise
  - class/unclassified-parameter
  - source/sourced
  - audit/confirmed
---

# Zero-lift angle from context

**Definition.** Zero-lift angle of attack read out of the cached assumption computation context.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
raw_alpha_0 = ctx.get("alpha_0_deg"); alpha_0_from_ctx = float(raw_alpha_0) if raw_alpha_0 is not None else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:650` — `_build_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Alpha at best glide` · `Alpha at minimum sink` · `Alpha at stall`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 ('for cambered airfoils α_L=0 is typically negative, −2° to −3°'); Sadraey §5.4.3 feature 3 (α_o ≈ −2° clean)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
α_L=0 = α at which c_l = 0; = 0° symmetric, negative for cambered
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
