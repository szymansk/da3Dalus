---
name: rear-secondary-bending-fraction
kind: parameter
unit: dimensionless
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Rear secondary bending fraction

**Definition.** Fraction of the bending moment M(y) the rear spar also carries as genuine secondary bending.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.0`

**Formula — as the code writes it.**

```
rear_secondary_bending_fraction: float = Field(
    0.0,
    ge=0.0,
    le=1.0,
    ...
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_plan.py:144` — `SparPlanRequest.rear_secondary_bending_fraction`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Rear-spar secondary bending share`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:438` · `app/services/spar_plan_service.py:454`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. No source read gives a fraction of primary bending carried by the rear spar. The default 0.0 means the sourced secondary-bending mechanism (Scholz §7.4; Lennon Ch. 13 hinge loads and flap lift increment) is switched OFF by default, and frontend/hooks/useSparPlan.ts buildPlanBody never sends the field, so no browser-originated plan can switch it on.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Not reachable from the UI: frontend/hooks/useSparPlan.ts buildPlanBody never sends it, so every browser-originated plan uses 0.0.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gh-1038: Fraction of the bending moment M(y) the rear spar also carries as genuine secondary bending, added on top of the torsion reaction. Default 0 (rear is torsion-only).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
