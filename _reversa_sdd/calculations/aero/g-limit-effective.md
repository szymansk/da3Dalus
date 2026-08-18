---
name: g-limit-effective
symbol: n
kind: quantity
unit: g
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
  - flag/scale
---

# Effective manoeuvre load factor

**Definition.** g_limit resolved from design assumptions, or the 3.0 default with a warning flag.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
g_limit_raw = get_effective_assumption(db, aeroplane_id, "g_limit"); g_limit = _G_LIMIT_DEFAULT (fallback) else float(g_limit_raw)
```

**Inputs.**

- [[aero-spanwise--g-limit-default|Default manoeuvre load factor]]  — *⤵ fallback*

**Produced by.** `app/services/analysis_service.py:2153` — `_compute_spar_sizing_for_surfaces`

**Consumed by.**

- in this graph: `g_limit fallback flag` · `Per-surface spar sizing block`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_spar_sizing` · `SparSizingResult`

**Source.** 🟢 SOURCED

> Sadraey §10.4.1 Table 10.9 and Eq. 10.4 (Wiley 2013)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
n_ult = 1.5 · n_max   (10.4)
```

**⚠️ Divergence from the source.** The design-assumption path is correct in principle (the user supplies n_max). The fallback path inherits the unattributed 3.0 — see g-limit-default.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023: no RC/UAV-scale validation of the default.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
