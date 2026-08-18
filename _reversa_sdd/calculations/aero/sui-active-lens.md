---
name: sui-active-lens
symbol: —
kind: quantity
unit: enum
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

# active_lens

**Definition.** Which score drives the ranking: mission > target_cl_cruise > re_agnostic.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if has_mission: active_lens = "mission" ... elif has_cruise: active_lens = "target_cl_cruise" ... else: active_lens = "re_agnostic"
```

**Inputs.**

- [[alr-score-mission|Mission suitability score]]  — *⊣ limit*
- [[alr-score-target-cl|target-CL suitability score]]  — *⊣ limit*
- [[alr-score-re-agnostic|re_agnostic suitability score]]  — *⊣ limit*

**Produced by.** `app/services/suitability_service.py:628` — `search_suitability`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SuitabilityQuery.active_lens:695` · `frontend useAirfoilSuitability.ts`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Product/UX precedence rule, not an engineering quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `has_mission = any(item.mission is not None for item in items)
has_cruise = any(item.target_cl_cruise is not None for item in items)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
