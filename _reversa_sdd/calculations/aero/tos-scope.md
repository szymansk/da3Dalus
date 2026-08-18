---
name: tos-scope
symbol: scope
kind: parameter
unit: n/a
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-strips
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Optimiser scope

**Definition.** Selects per-section, per-segment or whole-wing trip optimisation.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `"section" (default)`

**Formula — as the code writes it.**

```
scope: Literal["section", "segment", "whole"] = "section"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:459` — `run_turbulator_optimizer`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorOptimizeRequest.scope` · `frontend/components/workbench/TurbulatorEditDialog.tsx`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** API design, not a calculation. The finding stands as reported: 'segment' is advertised in the schema and UI but executes the 'section' branch, so the response echoes a scope that was never performed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 'segment' is offered in the API schema and UI but is handled identically to 'section' (line 493) — the response echoes scope='segment' while doing per-section work.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:459,493`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
