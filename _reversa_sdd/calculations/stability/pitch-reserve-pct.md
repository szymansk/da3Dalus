---
name: pitch-reserve-pct
symbol: —
kind: quantity
unit: %
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Elevator reserve percentage (summary text)

**Definition.** Percentage of pitch-control travel still available, rendered into the human-readable trim summary.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
reserve_pct = (1 - reserve.usage_fraction) * 100
```

**Inputs.**

- [[deflection-usage-fraction|Deflection usage fraction]]

**Produced by.** `app/services/trim_enrichment_service.py:348` — `generate_result_summary`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:349,361-374 (result_summary strings)` · `frontend/components/workbench/trim-interpretation/AnalysisGoalCard.tsx`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.5 steps 18–19 — the trim curve δ_E vs airspeed exists precisely so the designer can see how much of the deflection envelope is consumed at each condition and compare it against the limit from step 4.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
reserve = δ_E,max − |δ_E,required|, conventionally expressed as a fraction of δ_E,max
```

**⚠️ Divergence from the source.** Sadraey's comparison is bounded — exceeding the limit means the design fails and returns upstream (step 19). The code's percentage can go negative and is rendered unclamped, so a surface at 130 % usage reports '−30 % elevator reserve' rather than 'infeasible'. Its role filter ('elevator','stabilator','elevon','ruddervator') also omits 'flaperon', which _PITCH_ROLES in elevator_authority_service includes.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Can go negative (usage > 1) and is rendered with no clamp — a surface at 130 % usage reports '-30% elevator reserve'. Its role filter ('elevator','stabilator','elevon','ruddervator') omits 'flaperon', which _PITCH_ROLES in elevator_authority_service includes.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
