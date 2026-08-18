---
name: tos-xtr-lower
symbol: xtr_lower
kind: parameter
unit: x/c
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/aero-strips
  - class/unclassified-parameter
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Lower-surface trip position

**Definition.** Lower-surface transition is always left at natural (x/c = 1.0).

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.0`

**Formula — as the code writes it.**

```
xtr_lower: float = 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:125` — `_cd_at_cl_xtr`

**Consumed by.**

- in this graph: `Section cd at a target CL and trip position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/turbulator_optimizer_service.py:_cd_at_cl_xtr`

**Source.** 🟢 SOURCED

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (trip location convention: natural transition is the default case, 80% of training data); RC-Network Wiki, 'Turbulator (Aerodynamik)'
>
> — via `aerosandbox-expert, rc-aircraft-designer`

**The source states it as.**

```
xtr = 1.0 denotes free (natural) transition — no forced trip
```

**⚠️ Divergence from the source.** The value's MEANING is sourced and correct. What is unsourced is the modelling restriction it imposes: the cited RC-Network Wiki article describes turbulators generally (tape, wire fences, bleed, roughness) and nowhere restricts them to the upper surface, yet no caller can ever set xtr_lower, so a lower-surface turbulator is unrepresentable in this app.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No caller ever passes xtr_lower, so a lower-surface turbulator can never be modelled — a parameter that is complete but unreachable (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:125`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
