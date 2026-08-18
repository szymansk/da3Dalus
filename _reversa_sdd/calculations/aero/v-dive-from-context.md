---
name: v-dive-from-context
symbol: V_D
kind: parameter
unit: m/s
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/aero-spanwise
  - class/unclassified-parameter
  - source/no-source-found
  - flag/scale
---

# Dive speed from context

**Definition.** V_dive resolved from the cached assumption computation context, used only for the chart's upper axis bound.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
raw = context.get("v_dive_mps"); return float(raw)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:595` — `_resolve_v_dive_from_context`

**Consumed by.**

- in this graph: `Speed-polar X-axis upper bound`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> V_D (design dive speed) is a certification quantity (CS-23/CS-25 flight envelope); no source read in this pass defines it, and this slug is only a context read — the producing authority is elsewhere.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Scale (ADR 0023).** A CS-23/CS-25 design dive speed has no RC/UAV counterpart in the 0.5–15 kg class; ADR 0023 applies wherever the producing site adopted it.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
