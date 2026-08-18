---
name: ss-t-target-min
symbol: t_target_min
kind: parameter
unit: min
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Target flight time

**Definition.** Mission duration the energy budget must cover. Rejected at <= 0 with a domain error.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `10.0`

**Formula — as the code writes it.**

```
t_target_min = assumptions.t_target_min ; if t_target_min <= 0: raise ValidationDomainError(f"t_target_min must be > 0, got {t_target_min}")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:81` — `SolutionSpaceAssumptions.t_target_min`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Target flight time in hours`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:330` · `app/services/powertrain_solution_space_service.py:352` · `app/services/powertrain_solution_space_service.py:497` · `frontend/components/workbench/PowertrainTab.tsx:838`

**Source.** 🟡 PARTIAL

> Sadraey (2013), §8.7 bounds the class: 'The highest practical battery output is typically less than about 100 hp for less than an hour', and 'operating [a 2-hp electric motor] for 15 minutes requires about 400 g of battery.' A 10-minute default is inside that envelope but is not stated as a design value.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Mission requirement, not a physical constant. The schema default (10.0) and the frontend's rendered fallback (15) disagree, so the number shown does not match the number computed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Schema default is 10.0 but the frontend renders a fallback of 15 when unset (frontend/components/workbench/PowertrainTab.tsx:838, `assumptions.t_target_min ?? 15`) — the number shown in the input box does not match the number the backend uses when the field is omitted.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Target flight time [minutes]"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
