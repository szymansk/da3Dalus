---
name: low-re-score-r-poor
symbol: r_poor
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - audit/confirmed
  - flag/divergence
---

# Drag-rise ratio at which Match→0

**Definition.** CD(cl_target)/cd0 at which the target-CL Match component reaches zero.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `2.5`

**Formula — as the code writes it.**

```
low_re_score_r_poor: float = 2.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:102` — `Settings.low_re_score_r_poor`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Match component of score_target_cl`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_target_cl:1033,1055,1071`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for a drag-rise ratio of 2.5 as the zero-credit point.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# Relative drag-rise CD(CL_target)/cd0 at which Match→0  (gh-825 scoring).
low_re_score_r_poor: float = 2.5`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
