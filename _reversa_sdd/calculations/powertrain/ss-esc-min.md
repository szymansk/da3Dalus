---
name: ss-esc-min
symbol: ESC_min
kind: quantity
unit: A
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Minimum ESC current rating

**Definition.** Required ESC continuous current rating: peak current times the ESC margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
esc_min = i_peak * esc_margin
```

**Inputs.**

- [[ss-i-peak|Peak battery current]]
- [[ss-esc-margin|ESC current margin]]

**Produced by.** `app/services/powertrain_solution_space_service.py:149` — `_per_cell`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Catalog ESC match flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:427` · `app/services/powertrain_solution_space_service.py:450` · `app/services/powertrain_solution_space_service.py:480` · `frontend/components/workbench/PowertrainTab.tsx:127`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Motorsteller': ESC sizing is governed by 'maximum continuous current capacity', and advertised peak/pulse ratings are 'substantially higher than continuous rating' — i.e. the source establishes that a margin over the operating current is needed, but quotes no number.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
ESC continuous rating must exceed the sustained operating current
```

**⚠️ Divergence from the source.** The multiplier itself (1.4) is unattributed; see ss-esc-margin.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `module docstring: "ESC_min = I_peak × esc_margin"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
