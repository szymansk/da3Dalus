---
name: sui-conf-tier
symbol: —
kind: quantity
unit: ordinal
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Confidence sort tier

**Definition.** 0 for confident items, 1 for low-confidence; primary key of the ranking sort.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return 0 if item.min_analysis_confidence >= low_conf_flag else 1
```

**Inputs.**

- [[alr-min-analysis-confidence|Windowed min analysis confidence]]  — *⤵ fallback*
- [[low-re-low-confidence-flag|Low-confidence flag threshold]]  — *⊣ limit*

**Produced by.** `app/services/suitability_service.py:625` — `_conf_tier`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `search_suitability:629,632,635 (sort)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Ranking policy built on the unsourced 0.85 threshold; no domain source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `return 0 if item.min_analysis_confidence >= low_conf_flag else 1`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
