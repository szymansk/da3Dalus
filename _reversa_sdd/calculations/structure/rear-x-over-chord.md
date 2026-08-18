---
name: rear-x-over-chord
symbol: x/c_rear
kind: parameter
unit: dimensionless (x/c)
cluster: structure
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Rear-spar chord fraction (requested)

**Definition.** Requested chordwise location for the rear (torsion) spar.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.65`

**Formula — as the code writes it.**

```
rear_x_over_chord: float = Field(
    0.65,
    gt=0.0,
    lt=1.0,
    description="Chord fraction for the rear (torsion) spar. Default 0.65.",
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_plan.py:101` — `SparPlanRequest.rear_x_over_chord`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Clamped rear-spar chord location` · `Front–rear spar chordwise spacing`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:412` · `app/services/spar_plan_service.py:585` · `frontend/hooks/useSparPlan.ts:29`

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf / Aircraft Design (HAW Hamburg lecture notes), 07_WingDesign §7.4, p. 7-42 — "Typical locations for the spars are as follows: ... • Rear spar: 65% to 75% of the chord"
>
> — via `aircraft-design-scholz (lead)`

**The source states it as.**

```
Rear spar: 65% to 75% of the chord.
```

**⚠️ Divergence from the source.** 0.65 is the FORWARD END of Scholz's band, not its centre — i.e. the code defaults to the most conservative (most forward, most control-surface clearance) end of the cited range. That is a defensible choice but the code's description merely restates the number without saying so.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Scholz's 65-75% band is CS-25 transport-category and is set by the need to leave room for spoiler drive mechanisms and aileron linkages (Scholz §7.4 states this explicitly). RC/UAV wings at 0.5-15 kg have no such mechanisms. Sadraey §12.4.3(4) and Lennon Ch. 13 support the aft spar / hinge-line relationship at smaller scale but give no chord fraction. ADR 0023: 0.65c is not validated at RC/UAV scale by any source read.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number: the description restates the value without explaining it. No source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Chord fraction for the rear (torsion) spar. Default 0.65.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
