---
name: rear-moment-fn
symbol: M_rear(y)
kind: quantity
unit: N·m
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/divergence
  - flag/scale
---

# Rear-spar sizing moment

**Definition.** The total sizing moment for the rear spar: torsion reaction plus optional secondary bending. Replaces the primary bending moment as the rear spar's driver (gh-1038).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
def rear_moment_fn(y_span: float) -> float:
    reaction = torsion_fn(y_span) / spacing
    secondary = secondary_fraction * bending_fn(y_span)
    return reaction + secondary
```

**Inputs.**

- [[rear-torsion-reaction|Rear-spar torsion reaction]]
- [[rear-secondary-bending|Rear-spar secondary bending share]]

**Produced by.** `app/services/spar_plan_service.py:455` — `_make_rear_moment_fn`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Station design moment (plan path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:561` · `app/services/spar_plan_service.py:587` · `cad_designer/airplane/geometry/spar_solver.py:764`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 07_WingDesign §7.4 / [[wing-box-spars]] — the rear spar "carries secondary bending loads and provides torsional constraint" (i.e. both contributions, exactly the code's two terms)
>
> — via `aircraft-design-scholz (lead)`

**The source states it as.**

```
Scholz identifies the rear spar's two load contributions qualitatively: torsional constraint plus secondary bending. No source read gives them as a summed sizing moment.
```

**⚠️ Divergence from the source.** The two-term STRUCTURE (torsion reaction + secondary bending) matches Scholz's qualitative description. The torsion term inherits the dimensional defect documented at `rear-torsion-reaction`, so the sum adds a dimensionally-correct N·m term to a dimensionally-incorrect one.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Scholz §7.4 is CS-25 transport-category. ADR 0023.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `The rear spar's real job is to react the wing's torsion couple, NOT the primary bending moment.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
