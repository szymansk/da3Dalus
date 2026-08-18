---
name: n-span
symbol: n_span
kind: parameter
unit: count
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

# Number of spanwise stations

**Definition.** Number of spanwise sample stations per half, root-to-tip, that the solver samples the section at.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `6`

**Formula — as the code writes it.**

```
n_span: int = Field(
    6,
    ge=2,
    le=200,
    description="Number of spanwise sample stations per half (root->tip).",
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_plan.py:107` — `SparPlanRequest.n_span`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Spanwise sampling grid`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:569` · `cad_designer/airplane/geometry/spar_solver.py:745` · `frontend/hooks/useSparPlan.ts:30`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (no source read prescribes a number of spanwise sizing stations. Independent of provenance: it silently controls the reinforcement's structural length — see `reinforcement-reach` — and the start of the no-spar region, neither of which is a sampling concern)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Declared twice with the same default: app/schemas/spar_plan.py:107 and the function default cad_designer/airplane/geometry/spar_solver.py:720. It also silently controls the reinforcement's structural length (see reinforcement-reach), which is not a sampling concern.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Number of spanwise sample stations per half (root->tip).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
