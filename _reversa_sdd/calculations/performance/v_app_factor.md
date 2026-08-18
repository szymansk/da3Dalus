---
name: v_app_factor
symbol: k_app
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/scale
---

# Approach speed factor

**Definition.** Ratio of approach/touchdown speed to stall speed.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.3`

**Formula — as the code writes it.**

```
_V_APP_FACTOR: float = 1.3
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:105` — `_V_APP_FACTOR`

**Consumed by.**

- in this graph: `Approach speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_v_app:137`

**Source.** 🟢 SOURCED

> CS 25.125 (via Scholz 05_PreliminarySizing §5.1 and maximum-lift-coefficient-landing): landing distance from 50 ft determined with a stabilised approach at CAS not less than 1.3*V_S. Sadraey §4.3.2 concurs (approach/landing speeds typically 1.1-1.3 V_s).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_APP >= 1.3 * V_S
```

**⚠️ Scale (ADR 0023).** CS-25 is transport-category. The 1.3 margin is a certification minimum for manned aircraft; at RC scale a 1.3*V_S approach is conservative but not evidence-based for 0.5-15 kg.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `# V_app = 1.3 · V_S  ("V factors (Roskam standard)")`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
