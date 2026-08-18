---
name: alr-score-mission
symbol: —
kind: quantity
unit: dimensionless (0..1)
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

# Mission suitability score

**Definition.** re_agnostic multiplied by family, thickness and CL_max mission factors, clamped to [0,1].

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
mission_score = re_agnostic * family_bonus * thickness_match * cl_bonus
return float(min(max(mission_score, 0.0), 1.0))
```

**Inputs.**

- [[alr-score-re-agnostic|re_agnostic suitability score]]  — *⊣ limit*
- [[alr-family-bonus|Mission family bonus]]
- [[alr-thickness-match|Mission thickness match multiplier]]
- [[alr-cl-bonus|Mission CL_max bonus]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:939` — `score_mission`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `active_lens`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `suitability_service:474 → SuitabilityItem.mission` · `suitability_service:629 (ranking)` · `frontend AirfoilSuitabilityCard.tsx`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Multiplicative composition of three unsourced mission factors onto an unsourced base score; no source proposes this structure.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `mission_score = re_agnostic * family_bonus * thickness_match * cl_bonus`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
